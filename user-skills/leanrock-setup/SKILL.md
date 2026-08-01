---
name: leanrock-setup
description: Install, update, or diagnose LeanRock only when the user explicitly invokes `$leanrock-setup install`, `$leanrock-setup update`, or `$leanrock-setup doctor`.
---

# LeanRock setup

Parse exactly one action: `install`, `update`, or `doctor`. Do not act without an explicit action.

Read the LeanRock source path from the platform config:

- macOS/Linux: `~/.config/leanrock/config.json`
- Windows: `%APPDATA%\leanrock\config.json`

The config key `source` is the absolute LeanRock source repository. Validate that `VERSION` and
`install.py` exist there. The target is the current Git repository.

## install

1. Run `python3 <source>/install.py install <project>` (or `py -3` on Windows) as a dry-run.
2. Show every planned managed-file change and any unsafe merge.
3. Only after the user explicitly confirms applying that displayed plan, repeat with `--apply`.
4. Never commit, push, or trust hooks. Tell the user to open `/hooks`, inspect, and trust them.

## update

1. Compare `<project>/.leanrock/VERSION` with `<source>/VERSION`.
2. Run `install.py update <project>` and show the exact managed changes.
3. Never overwrite `.leanrock/state/CURRENT.md`.
4. Apply only after explicit confirmation, using `--apply`.
5. Never update business files outside managed blocks/files, commit, push, or trust hooks.

## doctor

Run `install.py doctor <project>`. It is read-only. Report the managed AGENTS block, four project
skills, hooks configuration and script, CURRENT.md, version, and hook trust reminder. Do not repair
anything unless the user later explicitly invokes install or update and confirms its dry-run.

If a merge is unsafe, stop that file and report why. Preserve all business content.
