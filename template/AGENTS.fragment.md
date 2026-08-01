<!-- LEANROCK:START -->
## LeanRock

Think deeply. Build lightly.

- Read `.leanrock/state/CURRENT.md` before work. The user's latest explicit statement wins.
- Understand the task, relevant code, and real call flow before minimizing a diff.
- Search before build: repository, existing types/callers, standard library, framework,
  database/native capabilities, and installed dependencies.
- For non-trivial work, record a short Reuse Check before the SPEC or implementation.
- Prefer current requirements over assumed future flexibility.
- Apply `REUSE → DELETE → MERGE → SIMPLIFY → ADD` in that order.
- Every new complexity must answer a current requirement or a real incident.
- “Future flexibility”, “clean architecture”, “best practice”, and “enterprise-ready”
  are not sufficient reasons by themselves.
- One real implementation does not prove a need for an abstraction.
- Do not default to single-implementation interfaces, one-product factories, registries,
  forwarding wrappers, speculative configuration, strategies, or compatibility layers.
- Fix the smallest shared root cause; search all relevant callers before a bug fix.
- Prefer deletion, boring code, few files, and the minimum correct diff.
- Make no “while I am here” or otherwise out-of-scope changes.
- Do not expand one concrete guard into a general guard framework.
- Keep the minimum effective test for non-trivial logic.
- Preserve real boundaries: authentication, authorization, payments, idempotency, privacy,
  provenance, destructive-operation safety, irreversible data protection, validation,
  loss-preventing error handling, accessibility, and explicitly retained behavior.
- Deliberate simplification uses `leanrock: <current ceiling>; upgrade when <measurable trigger>`.
- A non-trivial implementation defaults to one independent worktree, one main thread,
  and one explicit scope.
- Only the main Agent for the current worktree may modify `.leanrock/state/CURRENT.md`.
- Subagents treat state as read-only and return findings to the main Agent.
- Agent proposals are proposals, not Product Owner decisions.
- Do not guess unresolved questions or silently convert proposals into decisions.
- After decisions, scope, authorization, phase, blockers, or next steps change, the main
  Agent must update the checkpoint.
- SPEC approval is not implementation authorization; implementation authorization is not
  production-write authorization.
- Without explicit authorization, do not perform production, external, paid,
  irreversible, or destructive operations.
<!-- LEANROCK:END -->
