# Changelog

## 0.1.2 - 2026-08-01

- Installer boundary checks for symbolic links, Windows junctions, and resolved paths.
- Preflight validation of every managed target before writes begin.
- Atomic installer writes and backups.
- Tracked CURRENT template with automatic initialization in new worktrees.

## 0.1.1 - 2026-08-01

- Active root-session pointer for reliable checkpoint log selection.
- Valid-prefix recovery for corrupt turn logs.
- Lock-consistent turn-log reads and appends.
- File-based compact recovery without raw-turn `additionalContext` injection.
- Fail-open Hook output hardening.

## 0.1.0 - 2026-08-01

- Initial LeanRock rules.
- Ponytail-inspired implementation ladder.
- Search Before Build.
- Lean SPEC workflow.
- Lean implementation workflow.
- Complexity review.
- Checkpoint state.
- Exact-turn continuity recovery.
- Safe bootstrap and installer.
- Learning capture and promotion workflow.
