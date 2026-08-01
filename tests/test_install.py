from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.py"
BOOTSTRAP = ROOT / "bootstrap.py"


def run(*args: object, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)], text=True, capture_output=True, check=check
    )


def digest_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


class InstallTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="leanrock install 中文 ")
        self.project = Path(self.temp.name) / "business project 项目"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def install(self) -> subprocess.CompletedProcess[str]:
        return run(INSTALL, "install", self.project, "--apply")

    def test_new_git_project_install(self) -> None:
        self.install()
        self.assertTrue((self.project / "AGENTS.md").is_file())
        self.assertTrue((self.project / ".codex/hooks/leanrock_continuity.py").is_file())
        self.assertEqual((self.project / ".leanrock/VERSION").read_text().strip(), "0.1.2")
        self.assertTrue((self.project / ".leanrock/CURRENT.template.md").is_file())
        self.assertIn(".leanrock/state/ACTIVE_SESSION.json", (self.project / ".gitignore").read_text())

    def test_symlink_target_is_rejected_before_any_write(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("do not overwrite")
        version = self.project / ".leanrock/VERSION"
        version.parent.mkdir(parents=True)
        try:
            os.symlink(outside, version)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")

        result = run(INSTALL, "install", self.project, "--apply", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link or junction", result.stderr)
        self.assertEqual(outside.read_text(), "do not overwrite")
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_symlink_parent_is_rejected_before_any_write(self) -> None:
        outside = Path(self.temp.name) / "outside directory"
        outside.mkdir()
        agents = self.project / ".agents"
        try:
            os.symlink(outside, agents, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")

        result = run(INSTALL, "install", self.project, "--apply", check=False)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symbolic link or junction", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_existing_agents_content_is_preserved(self) -> None:
        original = "# Business rules\n\nDo not change invoices.\n"
        (self.project / "AGENTS.md").write_text(original)
        self.install()
        result = (self.project / "AGENTS.md").read_text()
        self.assertIn(original.strip(), result)
        self.assertIn("<!-- LEANROCK:START -->", result)

    def test_repeated_install_is_idempotent(self) -> None:
        self.install()
        before = digest_tree(self.project)
        result = self.install()
        self.assertIn("Applied 0 change(s)", result.stdout)
        self.assertEqual(before, digest_tree(self.project))
        self.assertEqual((self.project / "AGENTS.md").read_text().count("<!-- LEANROCK:START -->"), 1)
        self.assertEqual((self.project / ".gitignore").read_text().count("# LEANROCK:START"), 1)

    def test_existing_hooks_are_preserved(self) -> None:
        hooks = self.project / ".codex/hooks.json"
        hooks.parent.mkdir(parents=True)
        original = {
            "description": "business",
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo safe"}]}]},
        }
        hooks.write_text(json.dumps(original))
        self.install()
        merged = json.loads(hooks.read_text())
        self.assertEqual(merged["description"], "business")
        self.assertEqual(merged["hooks"]["PreToolUse"], original["hooks"]["PreToolUse"])
        self.assertTrue(all(event in merged["hooks"] for event in ("SessionStart", "SubagentStart", "UserPromptSubmit", "Stop")))

    def test_update_never_overwrites_current(self) -> None:
        self.install()
        current = self.project / ".leanrock/state/CURRENT.md"
        current.write_text("private current state 中文\n")
        run(INSTALL, "update", self.project, "--apply")
        self.assertEqual(current.read_text(), "private current state 中文\n")

    def test_new_worktree_initializes_current_from_tracked_template(self) -> None:
        self.install()
        subprocess.run(["git", "-C", str(self.project), "add", "-A"], check=True)
        subprocess.run(
            [
                "git", "-C", str(self.project), "-c", "user.name=LeanRock Tests",
                "-c", "user.email=tests@leanrock.local", "commit", "-qm", "install LeanRock",
            ],
            check=True,
        )
        worktree = Path(self.temp.name) / "new worktree 工作树"
        subprocess.run(
            ["git", "-C", str(self.project), "worktree", "add", "-qb", "test-worktree", str(worktree)],
            check=True,
        )
        try:
            current = worktree / ".leanrock/state/CURRENT.md"
            self.assertFalse(current.exists())
            hook = worktree / ".codex/hooks/leanrock_continuity.py"
            payload = json.dumps({
                "hook_event_name": "SessionStart",
                "session_id": "worktree-session",
                "source": "startup",
            })
            result = subprocess.run(
                [sys.executable, str(hook)], input=payload, text=True, capture_output=True, check=True,
                cwd=worktree,
            )
            json.loads(result.stdout)
            self.assertEqual(
                current.read_text(encoding="utf-8"),
                (worktree / ".leanrock/CURRENT.template.md").read_text(encoding="utf-8"),
            )
        finally:
            subprocess.run(
                ["git", "-C", str(self.project), "worktree", "remove", "--force", str(worktree)],
                check=True,
            )

    def test_dry_run_and_doctor_do_not_modify(self) -> None:
        before = digest_tree(self.project)
        result = run(INSTALL, "install", self.project)
        self.assertIn("Dry-run only", result.stdout)
        self.assertEqual(before, digest_tree(self.project))
        self.install()
        before = digest_tree(self.project)
        run(INSTALL, "doctor", self.project)
        self.assertEqual(before, digest_tree(self.project))

    def test_all_skills_disable_implicit_invocation(self) -> None:
        yamls = list(ROOT.glob("user-skills/*/agents/openai.yaml")) + list(
            ROOT.glob("template/.agents/skills/*/agents/openai.yaml")
        )
        self.assertEqual(len(yamls), 6)
        for path in yamls:
            self.assertIn("allow_implicit_invocation: false", path.read_text())

    def test_hook_template_registers_only_required_events_with_safe_limits(self) -> None:
        data = json.loads((ROOT / "template/.codex/hooks.json").read_text())
        self.assertEqual(set(data["hooks"]), {"SessionStart", "SubagentStart", "UserPromptSubmit", "Stop"})
        for event, groups in data["hooks"].items():
            handlers = [handler for group in groups for handler in group["hooks"]]
            self.assertEqual(len(handlers), 1)
            self.assertLessEqual(handlers[0]["timeout"], 5)
            self.assertIn("commandWindows", handlers[0])
            if event in {"SessionStart", "SubagentStart"}:
                self.assertEqual(handlers[0]["additionalContextLimit"], 2000)


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_apply_is_idempotent_and_preserves_other_skills(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leanrock home 中文 ") as raw:
            home = Path(raw)
            other = home / ".agents/skills/other-skill/SKILL.md"
            other.parent.mkdir(parents=True)
            other.write_text("keep")
            dry = run(BOOTSTRAP, "--home", home)
            self.assertIn("Dry-run only", dry.stdout)
            self.assertFalse((home / ".agents/skills/leanrock-setup").exists())
            run(BOOTSTRAP, "--home", home, "--apply")
            before = digest_tree(home)
            again = run(BOOTSTRAP, "--home", home, "--apply")
            self.assertIn("UNCHANGED", again.stdout)
            self.assertEqual(before, digest_tree(home))
            self.assertEqual(other.read_text(), "keep")
            config = json.loads((home / ".config/leanrock/config.json").read_text())
            self.assertEqual(config["source"], str(ROOT))


if __name__ == "__main__":
    unittest.main()
