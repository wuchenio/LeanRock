---
name: leanrock-spec
description: Produce a lean SPEC, workflow, database design, architecture, refactor plan, execution plan, or PR split only when explicitly invoked as `$leanrock-spec`.
---

# LeanRock SPEC

Default to read-only. Do not modify code. Read `AGENTS.md`, `.leanrock/state/CURRENT.md`, the
authoritative project documents, relevant code, and the real call flow. Never turn an Agent proposal
into an approved decision.

Before designing, search the repository, current types/functions/components/queries, standard
library, framework/native/database capabilities, and installed dependencies. For authentication,
authorization, cryptography, payments, protocols, timezone/calendar edges, complex parsers or file
formats, serialization standards, security-sensitive work, retries/distributed coordination, or a
small generic framework, also inspect current maintained official or mature solutions. A found
dependency is not permission to add it; new production dependencies require Product Owner approval.

Use this exact output:

## A. User-visible outcome
## B. Current real flow
## C. Reuse Check

- Existing repository implementation:
- Standard library:
- Framework/native/database capability:
- Already-installed dependency:
- Mature external solution required:
- Decision:

## D. Must-preserve invariants
## E. Minimum target flow

Keep this within one screen.

## F. REUSE / DELETE / MERGE / SIMPLIFY / ADD
## G. Complexity delta

Count before → after for tables; persisted states; queues/workers/cron; RPCs;
services/repositories/interfaces; dependencies; config flags; compatibility paths; and PR count.

## H. Rejected complexity
## I. Smallest vertical implementation sequence
## J. Genuine Product Owner decisions still required

Do not begin with tables, Services, files, or technical layers. Do not emit detailed file-level
instructions before architecture approval. Do not mechanically split PRs by Schema, Repository,
Service, Handler, Prompt, and UI. Do not introduce an abstraction before a second real consumer.
