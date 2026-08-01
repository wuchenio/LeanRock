---
name: leanrock-learn
description: Capture or promote LeanRock experience only when the user explicitly invokes `$leanrock-learn capture` or `$leanrock-learn promote`.
---

# LeanRock learning

Parse exactly one explicit action: `capture` or `promote`. Never write automatically.

## capture

After confirming the experience with the user, create one timestamped Markdown file in
`.leanrock/learnings/inbox/`. Record only:

- what happened;
- why it was a problem;
- current project;
- actual impact;
- smallest possible rule;
- whether the rule increases token or operational cost;
- whether a similar LeanRock rule already exists.

Do not modify the LeanRock source repository. Do not store secrets or full chat history.

## promote

Classify the item first:

A. temporary current state;
B. single-project rule;
C. cross-project general rule.

Only C may be proposed for LeanRock, and only if it repeated in at least two projects or prevents
one real severe incident. Resolve the LeanRock source from its user config. Search existing rules
first and prefer tightening one existing rule. Do not add a Skill, Hook, or file unless the current
structure cannot carry the proven rule.

Show the minimum source diff proposal before editing. Apply it only after explicit Product Owner
approval. Then update `VERSION` and `CHANGELOG.md`, add the smallest regression test, and run the
full test suite. Never update business projects, commit, push, or perform external writes.
