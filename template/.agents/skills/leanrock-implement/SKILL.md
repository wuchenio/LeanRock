---
name: leanrock-implement
description: Implement only an explicitly approved scope, and only when the user explicitly invokes `$leanrock-implement`.
---

# LeanRock implementation

Implement only the explicitly approved scope. SPEC approval alone is not implementation
authorization.

Before editing:

1. Read `AGENTS.md`.
2. Read `.leanrock/state/CURRENT.md`.
3. Read authoritative project documentation.
4. Complete the Reuse Check below.
5. Trace the real call flow.
6. Search all relevant callers.

## Reuse Check

- Existing repository implementation:
- Standard library:
- Framework/native/database capability:
- Already-installed dependency:
- Mature external solution required:
- Decision:

Fix the shared root cause. Use the fewest files and minimum correct diff. Do not perform nearby
cleanup, future configuration, speculative abstraction, or compatibility work. Prefer standard
library, native capabilities, and installed dependencies. Before hand-writing high-risk standard
functionality, inspect maintained official or mature solutions. Explain total ownership cost and
obtain Product Owner approval before adding any production dependency.

Use the project's existing test framework. Keep the minimum effective test for non-trivial logic.
Record out-of-scope issues without implementing them. Preserve security, data-loss, accessibility,
validation, and other real incident boundaries. Mark deliberate ceilings as
`leanrock: <current ceiling>; upgrade when <measurable trigger>`.

After implementation, explicitly invoke or follow `$leanrock-checkpoint` to update CURRENT.md with
the completed progress and next step. Report:

- changed files;
- tests/checks;
- complexity added;
- complexity removed;
- dependencies added;
- follow-ups noted but not done.
