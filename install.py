#!/usr/bin/env python3
"""Safely install, update, or inspect LeanRock in a Git repository."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template"
START = "<!-- LEANROCK:START -->"
END = "<!-- LEANROCK:END -->"
GIT_START = "# LEANROCK:START"
GIT_END = "# LEANROCK:END"
SKILLS = ("leanrock-spec", "leanrock-implement", "leanrock-review", "leanrock-checkpoint")
HOOK_EVENTS = ("SessionStart", "SubagentStart", "UserPromptSubmit", "Stop")


@dataclass
class Change:
    path: Path
    content: bytes
    reason: str


def git_root(project: Path) -> Path | None:
    current = project.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def managed_block(text: str, start_marker: str = START, end_marker: str = END) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end < 0 or end < start:
        raise ValueError("template managed block is missing or malformed")
    return text[start : end + len(end_marker)]


def merge_block(
    existing: str,
    block: str,
    start_marker: str = START,
    end_marker: str = END,
) -> str:
    start_count, end_count = existing.count(start_marker), existing.count(end_marker)
    if start_count != end_count or start_count > 1:
        raise ValueError("ambiguous LeanRock managed block")
    if start_count == 1:
        start = existing.index(start_marker)
        end = existing.index(end_marker) + len(end_marker)
        return existing[:start] + block + existing[end:]
    separator = "" if not existing else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + separator + block + "\n"


def hook_command() -> str:
    return 'python3 "$(git rev-parse --show-toplevel)/.codex/hooks/leanrock_continuity.py"'


def hook_windows() -> str:
    script = '$root = git rev-parse --show-toplevel; $script = Join-Path $root ".codex\\hooks\\leanrock_continuity.py"; '
    return script + 'if (Get-Command py -ErrorAction SilentlyContinue) { py -3 $script } elseif (Get-Command python -ErrorAction SilentlyContinue) { python $script }'


def desired_handler(event: str) -> dict:
    handler = {
        "type": "command",
        "command": hook_command(),
        "commandWindows": hook_windows(),
        "timeout": 5,
    }
    if event in ("SessionStart", "SubagentStart"):
        handler["additionalContextLimit"] = 2000
    return handler


def merge_hooks(existing: str) -> str:
    try:
        data = json.loads(existing) if existing.strip() else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"hooks.json is invalid JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hooks", {}), dict):
        raise ValueError("hooks.json must contain an object-valued hooks field")
    hooks = data.setdefault("hooks", {})
    for event in HOOK_EVENTS:
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise ValueError(f"hooks.{event} must be an array")
        matches = []
        for group in groups:
            if not isinstance(group, dict) or not isinstance(group.get("hooks", []), list):
                raise ValueError(f"hooks.{event} contains an unsafe shape")
            for handler in group.get("hooks", []):
                if isinstance(handler, dict) and "leanrock_continuity.py" in str(handler.get("command", "")):
                    matches.append((group, handler))
        if len(matches) > 1:
            raise ValueError(f"hooks.{event} has multiple LeanRock handlers")
        wanted = desired_handler(event)
        if matches:
            group, handler = matches[0]
            handler.clear()
            handler.update(wanted)
            if event == "SessionStart":
                group["matcher"] = "startup|resume|clear|compact"
        else:
            group = {"hooks": [wanted]}
            if event == "SessionStart":
                group["matcher"] = "startup|resume|clear|compact"
            groups.append(group)
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def managed_targets(project: Path, mode: str) -> list[Path]:
    targets = [
        project / "AGENTS.md",
        project / ".codex/hooks/leanrock_continuity.py",
        project / ".codex/hooks.json",
        project / ".gitignore",
        project / ".leanrock/CURRENT.template.md",
        project / ".leanrock/VERSION",
        project / ".leanrock/backups",
    ]
    for name in SKILLS:
        targets.extend([
            project / ".agents/skills" / name / "SKILL.md",
            project / ".agents/skills" / name / "agents/openai.yaml",
        ])
    if mode == "install":
        targets.append(project / ".leanrock/state/CURRENT.md")
    return targets


def link_like(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & reparse)


def path_error(project: Path, target: Path) -> str | None:
    root = project.resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return f"{target}: target is outside the Git root"

    current = target
    while True:
        if link_like(current):
            return f"{target.relative_to(root)}: target or existing parent is a symbolic link or junction"
        if current != target and current.exists() and not current.is_dir():
            return f"{target.relative_to(root)}: existing parent is not a directory"
        if current == root:
            break
        current = current.parent

    backup_root = root / ".leanrock/backups"
    if target == backup_root and target.exists() and not target.is_dir():
        return ".leanrock/backups: backup path is not a directory"
    if target != backup_root and target.exists() and not target.is_file():
        return f"{target.relative_to(root)}: managed file target is not a regular file"

    try:
        target.resolve(strict=False).relative_to(root)
    except ValueError:
        return f"{target.relative_to(root)}: resolved target is outside the Git root"
    return None


def preflight(project: Path, mode: str) -> list[str]:
    return [error for target in managed_targets(project, mode) if (error := path_error(project, target))]


def collect(project: Path, mode: str) -> tuple[list[Change], list[str]]:
    changes: list[Change] = []
    errors = preflight(project, mode)
    if errors:
        return changes, errors

    def propose(relative: str, content: bytes, reason: str, only_if_missing: bool = False) -> None:
        target = project / relative
        if only_if_missing and target.exists():
            return
        try:
            current = target.read_bytes()
        except FileNotFoundError:
            current = None
        if current != content:
            changes.append(Change(target, content, reason))

    try:
        agents_template = read_text(TEMPLATE / "AGENTS.fragment.md")
        agents = merge_block(read_text(project / "AGENTS.md"), managed_block(agents_template))
        propose("AGENTS.md", agents.encode(), "managed AGENTS block")
    except ValueError as exc:
        errors.append(f"AGENTS.md: {exc}")

    for name in SKILLS:
        for suffix in ("SKILL.md", "agents/openai.yaml"):
            rel = Path(".agents/skills") / name / suffix
            propose(str(rel), (TEMPLATE / rel).read_bytes(), "managed project skill")

    propose(".codex/hooks/leanrock_continuity.py", (TEMPLATE / ".codex/hooks/leanrock_continuity.py").read_bytes(), "managed continuity hook")
    try:
        hooks = merge_hooks(read_text(project / ".codex/hooks.json"))
        propose(".codex/hooks.json", hooks.encode(), "merged hook handlers")
    except ValueError as exc:
        errors.append(f".codex/hooks.json: {exc}")

    gitignore_template = read_text(TEMPLATE / "gitignore.fragment")
    try:
        gitignore = merge_block(
            read_text(project / ".gitignore"),
            managed_block(gitignore_template, GIT_START, GIT_END),
            GIT_START,
            GIT_END,
        )
        propose(".gitignore", gitignore.encode(), "managed gitignore block")
    except ValueError as exc:
        errors.append(f".gitignore: {exc}")

    current_template = (TEMPLATE / ".leanrock/state/CURRENT.example.md").read_bytes()
    propose(".leanrock/CURRENT.template.md", current_template, "worktree state template")
    if mode == "install":
        propose(".leanrock/state/CURRENT.md", current_template, "initial state", only_if_missing=True)
    propose(".leanrock/VERSION", (ROOT / "VERSION").read_bytes(), "installed version")
    return changes, errors


def backup(project: Path, target: Path) -> None:
    if not target.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    relative = target.relative_to(project)
    destination = project / ".leanrock" / "backups" / stamp / relative
    error = path_error(project, project / ".leanrock/backups")
    if error:
        raise ValueError(error)
    atomic_write_bytes(destination, target.read_bytes(), target.stat().st_mode & 0o777)


def atomic_write_bytes(target: Path, content: bytes, mode: int = 0o644) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, target)
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass


def apply_changes(project: Path, changes: list[Change], mode: str) -> None:
    errors = preflight(project, mode)
    if errors:
        raise ValueError("; ".join(errors))
    for change in changes:
        error = path_error(project, change.path)
        if error:
            raise ValueError(error)
        backup(project, change.path)
        existing_mode = change.path.stat().st_mode & 0o777 if change.path.exists() else 0o644
        atomic_write_bytes(change.path, change.content, existing_mode)


def doctor(project: Path) -> int:
    before = {p: p.stat().st_mtime_ns for p in project.rglob("*") if p.is_file()}
    changes, errors = collect(project, "update")
    checks = {
        "managed AGENTS block": START in read_text(project / "AGENTS.md") and END in read_text(project / "AGENTS.md"),
        "four project skills": all((project / ".agents/skills" / name / "SKILL.md").is_file() for name in SKILLS),
        "hooks.json": (project / ".codex/hooks.json").is_file(),
        "hook script": (project / ".codex/hooks/leanrock_continuity.py").is_file(),
        "CURRENT.md": (project / ".leanrock/state/CURRENT.md").is_file(),
        "installed version": read_text(project / ".leanrock/VERSION").strip() == read_text(ROOT / "VERSION").strip(),
    }
    for label, ok in checks.items():
        print(f"{'OK' if ok else 'MISSING'} {label}")
    for error in errors:
        print(f"ERROR {error}")
    if changes:
        print(f"UPDATE AVAILABLE {len(changes)} managed file(s)")
    print("HOOK TRUST REVIEW: open /hooks after installation or any hook definition change.")
    after = {p: p.stat().st_mtime_ns for p in project.rglob("*") if p.is_file()}
    if before != after:
        print("ERROR doctor modified files", file=sys.stderr)
        return 1
    return 1 if errors or not all(checks.values()) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install LeanRock into a Git repository.")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("install", "update"):
        p = sub.add_parser(command)
        p.add_argument("project", type=Path)
        p.add_argument("--apply", action="store_true")
    p = sub.add_parser("doctor")
    p.add_argument("project", type=Path)
    args = parser.parse_args()
    project = git_root(args.project)
    if project is None:
        print("ERROR target must be inside a Git repository", file=sys.stderr)
        return 2
    if args.command == "doctor":
        return doctor(project)
    changes, errors = collect(project, args.command)
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    for change in changes:
        print(f"{'APPLY' if args.apply else 'WOULD WRITE'} {change.path.relative_to(project)} — {change.reason}")
    if errors:
        print("Unsafe files were not written.", file=sys.stderr)
        return 1
    if not getattr(args, "apply", False):
        print("Dry-run only. Re-run with --apply to write files.")
        return 0
    try:
        apply_changes(project, changes, args.command)
    except (OSError, ValueError) as exc:
        print(f"ERROR no further files were written: {exc}", file=sys.stderr)
        return 1
    print(f"Applied {len(changes)} change(s). No commit, push, or hook trust was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
