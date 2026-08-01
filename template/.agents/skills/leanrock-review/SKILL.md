---
name: leanrock-review
description: Read-only complexity review of the current diff, or an explicitly named repository scope, only when invoked as `$leanrock-review`.
---

# LeanRock review

Review only; do not modify files. Default scope is the current diff. Use a wider repository scope
only when the user explicitly names it. Read relevant code and callers before suggesting deletion.

Allowed labels: `delete`, `reuse`, `stdlib`, `native`, `dependency`, `yagni`, `merge`, `shrink`,
`guard-required`, `guard-bloat`.

For every finding, report:

- location;
- current complexity;
- minimum alternative;
- whether it affects correctness or an incident boundary.

Separate required authentication, authorization, payments, idempotency, privacy, provenance,
destructive-operation/data-loss, validation, loss-preventing errors, and accessibility guards from
generic frameworks created in the name of safety. A concrete necessary guard is not guard bloat.

End with:

- files possibly removable;
- dependencies possibly removable;
- concepts possibly removable;
- estimated net LOC reduction (write `unknown` when it cannot be estimated reliably).

If nothing can be removed, output exactly: `Lean already. Ship.`
