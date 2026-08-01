---
name: leanrock-checkpoint
description: Maintain only `.leanrock/state/CURRENT.md` from confirmed evidence, only when explicitly invoked as `$leanrock-checkpoint`.
---

# LeanRock checkpoint

Modify only `.leanrock/state/CURRENT.md`. Only the main Agent for the current worktree may do so;
subagents must return findings without editing state.

Read, in this order:

1. the current user message;
2. current `.leanrock/state/CURRENT.md`;
3. the current session's exact `.leanrock/state/turns/<session_id>.jsonl` log in full;
4. Git branch, worktree, and `git status`;
5. authoritative project documents needed to resolve recorded facts.

Put only user-confirmed facts in `Confirmed decisions`. Put Agent ideas in `Proposed but not
approved`. Put unresolved matters in `Open questions`. Never equate SPEC approval with implementation
authorization, implementation authorization with production-write authorization, or guess a
resolution to conflicting evidence.

Keep current scope/authorization, phase, completed work, blockers, and next step concise. Do not save
full chat history, a full SPEC, code, secrets, or an append-only history. Keep the whole file at or
below 100 lines by replacing stale status with current status.

After the successful content update, reread the turns log and update frontmatter:

- `leanrock_state_version` (currently `1`);
- `updated_at` as UTC ISO 8601;
- `last_incorporated_session_id`;
- `last_incorporated_seq`.

Mark only the highest sequence actually read and absorbed. If the session cannot be identified or the
log cannot be fully read, do not advance the marker. Re-read CURRENT.md and verify its claims and line
count before reporting success.
