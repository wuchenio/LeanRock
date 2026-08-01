#!/usr/bin/env python3
"""Install LeanRock's two user-level skills. Dry-run unless --apply is used."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parent
SKILL_NAMES = ("leanrock-setup", "leanrock-learn")


def config_path(home: Path) -> Path:
    appdata = os.environ.get("APPDATA")
    if os.name == "nt" and appdata:
        return Path(appdata) / "leanrock" / "config.json"
    return home / ".config" / "leanrock" / "config.json"


def backup_path(target: Path, home: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return home / ".config" / "leanrock" / "backups" / stamp / target.name


def identical_tree(source: Path, target: Path) -> bool:
    if not target.is_dir():
        return False
    source_files = sorted(p.relative_to(source) for p in source.rglob("*") if p.is_file())
    target_files = sorted(p.relative_to(target) for p in target.rglob("*") if p.is_file())
    return source_files == target_files and all(
        (source / rel).read_bytes() == (target / rel).read_bytes() for rel in source_files
    )


def run(apply: bool, home: Path) -> int:
    destination = home / ".agents" / "skills"
    actions: list[tuple[Path, Path]] = []
    for name in SKILL_NAMES:
        source = SOURCE_ROOT / "user-skills" / name
        target = destination / name
        if not source.is_dir():
            print(f"ERROR missing source skill: {source}", file=sys.stderr)
            return 1
        if identical_tree(source, target):
            print(f"UNCHANGED {target}")
        else:
            actions.append((source, target))
            print(f"{'APPLY' if apply else 'WOULD INSTALL'} {target}")

    cfg = config_path(home)
    desired = {"source": str(SOURCE_ROOT)}
    cfg_same = False
    try:
        cfg_same = json.loads(cfg.read_text(encoding="utf-8")) == desired
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    if cfg_same:
        print(f"UNCHANGED {cfg}")
    else:
        print(f"{'APPLY' if apply else 'WOULD WRITE'} {cfg}")

    if not apply:
        print("Dry-run only. Re-run with --apply to write files.")
        return 0

    destination.mkdir(parents=True, exist_ok=True)
    for source, target in actions:
        if target.exists():
            backup = backup_path(target, home)
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(target, backup)
            shutil.rmtree(target)
            print(f"BACKUP {target} -> {backup}")
        shutil.copytree(source, target)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if cfg.exists() and not cfg_same:
        backup = backup_path(cfg, home)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cfg, backup)
    cfg.write_text(json.dumps(desired, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        cfg.chmod(0o600)
    except OSError:
        pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Install LeanRock user skills (dry-run by default).")
    parser.add_argument("--apply", action="store_true", help="write changes")
    parser.add_argument("--home", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    return run(args.apply, (args.home or Path.home()).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
