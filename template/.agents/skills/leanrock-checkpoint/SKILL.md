---
name: leanrock-checkpoint
description: Maintain only `.leanrock/state/CURRENT.md` from confirmed evidence, only when explicitly invoked as `$leanrock-checkpoint`.
---

# LeanRock checkpoint

Modify only `.leanrock/state/CURRENT.md`. Only the main Agent for the current worktree may do so;
subagents must return findings without editing state.

Use the current user message, then read in this order:

1. `.leanrock/state/ACTIVE_SESSION.json`;
2. current `.leanrock/state/CURRENT.md`;
3. the exact `turn_log` named by ACTIVE_SESSION, after verifying it stays under
   `.leanrock/state/turns/`;
4. Git branch, worktree, and `git status`;
5. authoritative project documents needed to resolve recorded facts.

Do not guess the active session from the newest file, scan all sessions to choose one, rely on chat
memory, or parse a Codex transcript. If ACTIVE_SESSION is missing or invalid, stop without advancing
the incorporated marker.

Do not reread the full session history on every checkpoint. From the named turn log, read all exact
records after `last_incorporated_seq`, plus the most recent six records as a context tail. Merge by
`seq`, deduplicate, and preserve original order. If CURRENT names a different incorporated session,
treat all records in the active session as unincorporated.

Put only user-confirmed facts in `Confirmed decisions`. Put Agent ideas in `Proposed but not
approved`. Put unresolved matters in `Open questions`. Never equate SPEC approval with implementation
authorization, implementation authorization with production-write authorization, or guess a
resolution to conflicting evidence.

Keep current scope/authorization, phase, completed work, blockers, and next step concise. Do not save
full chat history, a full SPEC, code, secrets, or an append-only history. Keep the whole file at or
below 100 lines by replacing stale status with current status.

After the successful content update, reread the exact records selected above and update frontmatter:

- `leanrock_state_version` (currently `1`);
- `updated_at` as UTC ISO 8601;
- `last_incorporated_session_id`;
- `last_incorporated_seq`.

Mark only the highest sequence actually read and absorbed. Do not advance to ACTIVE_SESSION's
`latest_seq` unless that exact record was read and absorbed. If the selected records cannot be fully
read, do not advance the marker. Re-read CURRENT.md and verify its claims and line count before
reporting success.
