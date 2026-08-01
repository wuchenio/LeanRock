from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK_SOURCE = ROOT / "template/.codex/hooks/leanrock_continuity.py"


class ContinuityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="leanrock hook 中文 ")
        self.project = Path(self.temp.name) / "repo with spaces 项目"
        self.hook = self.project / ".codex/hooks/leanrock_continuity.py"
        self.hook.parent.mkdir(parents=True)
        shutil.copy2(HOOK_SOURCE, self.hook)
        (self.project / ".git").mkdir()
        self.state = self.project / ".leanrock/state"
        self.state.mkdir(parents=True)
        self.write_current(None, 0)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_current(self, session: str | None, seq: int, body: str = "# Current State\n\nNo secrets.") -> None:
        value = "null" if session is None else session
        (self.state / "CURRENT.md").write_text(
            "---\nleanrock_state_version: 1\nupdated_at: null\n"
            f"last_incorporated_session_id: {value}\nlast_incorporated_seq: {seq}\n---\n\n{body}\n",
            encoding="utf-8",
        )

    def invoke(self, event: str, session: str = "session-A", **fields: object) -> subprocess.CompletedProcess[str]:
        payload = {
            "hook_event_name": event,
            "session_id": session,
            "turn_id": fields.pop("turn_id", "turn-1"),
            "cwd": str(self.project),
            **fields,
        }
        return subprocess.run(
            [sys.executable, str(self.hook)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            cwd=self.project,
            timeout=5,
            check=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )

    def records(self, session: str = "session-A") -> list[dict]:
        path = self.state / "turns" / f"{session}.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def add_pair(self, index: int, session: str = "session-A") -> None:
        self.invoke("UserPromptSubmit", session, turn_id=f"u{index}", prompt=f"用户 message {index}")
        result = self.invoke("Stop", session, turn_id=f"a{index}", last_assistant_message=f"Assistant reply {index}")
        self.assertEqual(json.loads(result.stdout), {})

    def test_user_and_stop_save_exact_unicode_messages_and_valid_json(self) -> None:
        user = "请保留原文 — English\n第二行"
        assistant = "完成 ✅\nExact assistant text."
        self.assertEqual(self.invoke("UserPromptSubmit", prompt=user).stdout, "")
        stop = self.invoke("Stop", last_assistant_message=assistant)
        self.assertEqual(json.loads(stop.stdout), {})
        items = self.records()
        self.assertEqual([x["text"] for x in items], [user, assistant])
        self.assertEqual([x["role"] for x in items], ["user", "assistant"])
        self.assertEqual([x["seq"] for x in items], [1, 2])

    def test_sessions_have_independent_logs_and_sequences(self) -> None:
        self.invoke("UserPromptSubmit", "one", prompt="first")
        self.invoke("UserPromptSubmit", "two", prompt="second")
        self.invoke("Stop", "one", last_assistant_message="third")
        self.assertEqual([x["seq"] for x in self.records("one")], [1, 2])
        self.assertEqual([x["seq"] for x in self.records("two")], [1])

    def test_marker_recovers_all_later_messages_not_fixed_to_one_or_two(self) -> None:
        for index in range(6):
            self.add_pair(index)
        self.write_current("session-A", 4)
        result = self.invoke("SessionStart", source="compact")
        payload = json.loads(result.stdout)
        recovery = (self.state / "RECOVERY.md").read_text()
        for index in range(2, 6):
            self.assertIn(f"用户 message {index}", recovery)
            self.assertIn(f"Assistant reply {index}", recovery)
        self.assertIn("用户 message 2", payload["hookSpecificOutput"]["additionalContext"])

    def test_recent_six_are_merged_deduplicated_in_original_order(self) -> None:
        for index in range(5):
            self.add_pair(index)
        self.write_current("session-A", 8)
        self.invoke("SessionStart", source="compact")
        recovery = (self.state / "RECOVERY.md").read_text()
        # Marker selects 9-10; six-item tail adds 5-8 once, yielding seq 5..10.
        self.assertNotIn("用户 message 0", recovery)
        self.assertEqual(recovery.count("用户 message 2"), 1)
        positions = [recovery.index(text) for text in ("用户 message 2", "Assistant reply 2", "用户 message 3", "Assistant reply 4")]
        self.assertEqual(positions, sorted(positions))

    def test_no_or_foreign_marker_treats_all_as_unincorporated(self) -> None:
        for index in range(4):
            self.add_pair(index)
        self.write_current("different-session", 999)
        self.invoke("SessionStart", source="compact")
        recovery = (self.state / "RECOVERY.md").read_text()
        self.assertIn("用户 message 0", recovery)
        self.assertIn("Assistant reply 3", recovery)

    def test_short_compact_directly_injects_exact_turns(self) -> None:
        self.add_pair(1)
        output = json.loads(self.invoke("SessionStart", source="compact").stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("用户 message 1", context)
        self.assertIn("Assistant reply 1", context)
        self.assertLessEqual(len(context), 7600)

    def test_long_compact_requires_full_recovery_read_and_is_bounded(self) -> None:
        long_text = "长消息abc" * 2500
        self.invoke("UserPromptSubmit", prompt=long_text)
        output = json.loads(self.invoke("SessionStart", source="compact").stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("read `.leanrock/state/RECOVERY.md` in full", context)
        self.assertLessEqual(len(context), 7600)
        self.assertIn(long_text, (self.state / "RECOVERY.md").read_text())

    def test_startup_resume_clear_are_valid_and_short(self) -> None:
        self.add_pair(1)
        for source in ("startup", "resume", "clear"):
            output = json.loads(self.invoke("SessionStart", source=source).stdout)
            context = output["hookSpecificOutput"]["additionalContext"]
            self.assertIn("LeanRock current state", context)
            self.assertLessEqual(len(context), 7600)

    def test_subagent_is_read_only_and_does_not_receive_turn_log(self) -> None:
        self.invoke("UserPromptSubmit", prompt="PRIVATE TURN SENTINEL")
        output = json.loads(self.invoke("SubagentStart", agent_id="sub", agent_type="explore").stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertIn("read-only for subagents", context)
        self.assertIn("do not modify", context)
        self.assertNotIn("PRIVATE TURN SENTINEL", context)

    def test_transcript_path_is_never_parsed(self) -> None:
        transcript = self.project / "unstable transcript.jsonl"
        transcript.write_text("SECRET_TRANSCRIPT_SENTINEL")
        result = self.invoke("SessionStart", source="compact", transcript_path=str(transcript))
        self.assertNotIn("SECRET_TRANSCRIPT_SENTINEL", result.stdout)
        self.assertNotIn("SECRET_TRANSCRIPT_SENTINEL", (self.state / "RECOVERY.md").read_text())

    def test_corrupt_log_backs_up_and_fails_open(self) -> None:
        turns = self.state / "turns"
        turns.mkdir()
        (turns / "session-A.jsonl").write_text("{broken json\n")
        result = self.invoke("UserPromptSubmit", prompt="after corruption")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.records()[0]["text"], "after corruption")
        self.assertTrue(list(turns.glob("session-A.jsonl.corrupt-*.bak")))

    def test_missing_state_fails_open(self) -> None:
        shutil.rmtree(self.state)
        result = self.invoke("SessionStart", source="compact")
        self.assertEqual(result.returncode, 0)
        self.assertIsInstance(json.loads(result.stdout), dict)

    def test_invalid_stdin_fails_open_without_network_or_dependencies(self) -> None:
        result = subprocess.run(
            [sys.executable, str(self.hook)], input="not json", text=True, capture_output=True,
            cwd=self.project, timeout=5,
        )
        self.assertEqual(result.returncode, 0)
        source = self.hook.read_text()
        for forbidden in ("requests", "urllib", "http.client", "socket", "openai"):
            self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
