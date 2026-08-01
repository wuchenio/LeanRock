#!/usr/bin/env python3
"""LeanRock exact-turn logging and bounded recovery context. Standard library only."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTEXT_LIMIT = 7600
CURRENT_LIMIT = 3000
TAIL_COUNT = 6


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_id(value: object) -> str:
    text = str(value or "unknown")
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", text)
    return cleaned[:160] or "unknown"


def repo_root() -> Path:
    # Installed location is <root>/.codex/hooks/this_file.py. No subprocess needed.
    script = Path(__file__).resolve()
    candidate = script.parents[2]
    if (candidate / ".git").exists():
        return candidate
    cwd = Path.cwd().resolve()
    for path in (cwd, *cwd.parents):
        if (path / ".git").exists():
            return path
    return candidate


def state_dir() -> Path:
    return repo_root() / ".leanrock" / "state"


def restrict(path: Path) -> None:
    try:
        path.chmod(0o600)
    except OSError:
        pass


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(text, encoding="utf-8")
    restrict(temp)
    os.replace(temp, path)
    restrict(path)


class Lock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "Lock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(50):
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > 10:
                        self.path.unlink()
                        continue
                except OSError:
                    pass
                time.sleep(0.02)
        raise TimeoutError("turn log lock unavailable")

    def __exit__(self, *_: object) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except OSError:
            pass


def corrupt_backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    destination = path.with_name(f"{path.name}.corrupt-{stamp}.bak")
    try:
        shutil.copy2(path, destination)
        restrict(destination)
    except OSError:
        pass


def read_records(path: Path, reset_corrupt: bool = False) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict) or not isinstance(item.get("seq"), int):
                raise ValueError("invalid turn record")
            records.append(item)
        return records
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        corrupt_backup(path)
        if reset_corrupt:
            atomic_write(path, "")
        return []


def append_turn(data: dict[str, Any], role: str, text: str) -> None:
    session_id = safe_id(data.get("session_id"))
    turns = state_dir() / "turns"
    path = turns / f"{session_id}.jsonl"
    with Lock(turns / f".{session_id}.lock"):
        records = read_records(path, reset_corrupt=True)
        seq = max((int(item["seq"]) for item in records), default=0) + 1
        record = {
            "seq": seq,
            "timestamp_utc": utc_now(),
            "session_id": str(data.get("session_id") or "unknown"),
            "turn_id": str(data.get("turn_id") or "unknown"),
            "role": role,
            "text": text,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        restrict(path)


def current_text() -> str:
    try:
        return (state_dir() / "CURRENT.md").read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, UnicodeError):
        return ""


def marker(current: str) -> tuple[str | None, int | None]:
    session = re.search(r"^last_incorporated_session_id:\s*[\"']?([^\n\"']*)", current, re.MULTILINE)
    seq = re.search(r"^last_incorporated_seq:\s*(\d+)", current, re.MULTILINE)
    return (session.group(1).strip() if session else None, int(seq.group(1)) if seq else None)


def select_records(records: list[dict[str, Any]], session_id: str, current: str) -> list[dict[str, Any]]:
    marked_session, marked_seq = marker(current)
    if marked_session == session_id and marked_seq is not None:
        selected_seq = {int(item["seq"]) for item in records if int(item["seq"]) > marked_seq}
    else:
        selected_seq = {int(item["seq"]) for item in records}
    selected_seq.update(int(item["seq"]) for item in records[-TAIL_COUNT:])
    return [item for item in records if int(item["seq"]) in selected_seq]


def render_recovery(session_id: str, records: list[dict[str, Any]]) -> str:
    lines = [
        "# LeanRock Recovery",
        "",
        "Accurate local turn records selected deterministically; no semantic summary was applied.",
        f"Session: `{session_id}`",
        "",
    ]
    for item in records:
        lines.extend([
            f"## seq {item.get('seq')} · {item.get('role')} · {item.get('timestamp_utc')}",
            "",
            "<leanrock-turn>",
            str(item.get("text", "")),
            "</leanrock-turn>",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"


def bounded(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit < 80:
        return text[:limit]
    half = (limit - 50) // 2
    return text[:half] + "\n...[bounded by LeanRock]...\n" + text[-half:]


def output_context(event: str, context: str) -> None:
    context = bounded(context, CONTEXT_LIMIT)
    payload = {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def session_context(data: dict[str, Any]) -> None:
    session_id = str(data.get("session_id") or "unknown")
    current = current_text()
    path = state_dir() / "turns" / f"{safe_id(session_id)}.jsonl"
    records = read_records(path, reset_corrupt=True)
    selected = select_records(records, session_id, current)
    recovery = render_recovery(session_id, selected)
    recovery_path = state_dir() / "RECOVERY.md"
    source = str(data.get("source") or "startup")

    if source == "compact":
        atomic_write(recovery_path, recovery)
        direct = "LeanRock current state:\n\n" + current + "\nLeanRock accurate recovery turns:\n\n" + recovery
        if len(direct) <= CONTEXT_LIMIT:
            context = direct
        else:
            preview_budget = CONTEXT_LIMIT - CURRENT_LIMIT - 360
            context = (
                "LeanRock current state (bounded):\n\n"
                + bounded(current, CURRENT_LIMIT)
                + "\n\nRecovery is too large for direct injection. Before reasoning further, editing files, "
                "or calling tools, read `.leanrock/state/RECOVERY.md` in full.\n\n"
                + bounded(recovery, max(200, preview_budget))
            )
        output_context("SessionStart", context)
        return

    marked_session, marked_seq = marker(current)
    pending = any(
        marked_session != session_id or marked_seq is None or int(item["seq"]) > marked_seq
        for item in records
    )
    if pending:
        atomic_write(recovery_path, recovery)
    note = (
        "\n\nUnincorporated exact turns exist. Read `.leanrock/state/RECOVERY.md` before relying on state."
        if pending else ""
    )
    output_context("SessionStart", "LeanRock current state:\n\n" + bounded(current, CURRENT_LIMIT) + note)


def subagent_context() -> None:
    current = bounded(current_text(), 1800)
    output_context(
        "SubagentStart",
        "LeanRock state is read-only for subagents. Return findings to the main agent; do not modify "
        "`.leanrock/state/CURRENT.md`.\n\nCurrent state (bounded):\n" + current,
    )


def read_input() -> dict[str, Any]:
    raw = sys.stdin.read()
    data = json.loads(raw.lstrip("\ufeff") or "{}")
    return data if isinstance(data, dict) else {}


def main() -> int:
    event = ""
    try:
        data = read_input()
        event = str(data.get("hook_event_name") or "")
        if event == "UserPromptSubmit":
            prompt = data.get("prompt")
            if isinstance(prompt, str):
                append_turn(data, "user", prompt)
        elif event == "Stop":
            message = data.get("last_assistant_message")
            if isinstance(message, str):
                append_turn(data, "assistant", message)
            sys.stdout.write("{}\n")
        elif event == "SessionStart":
            session_context(data)
        elif event == "SubagentStart":
            subagent_context()
    except Exception:
        # Continuity must never block Codex. Stop still requires valid JSON on success.
        if event == "Stop" or '"hook_event_name"' in locals().get("raw", ""):
            sys.stdout.write("{}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
