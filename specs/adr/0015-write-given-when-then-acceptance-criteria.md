---
status: accepted
date: 2026-11-11
---

# Write Given/When/Then acceptance criteria

## Context and Problem Statement

The functional specification needs testable acceptance criteria that tests can trace back to. Which format should they use?

## Considered Options

* Given/When/Then with a stable ID and a verification tag (`[test]`, `[live]`, `[manual]`), as in the author's other projects
* EARS ("WHEN ... THE SYSTEM SHALL ...")
* Plain checklists per tool, without IDs

## Decision Outcome

Chosen option: "Given/When/Then with a stable ID and a verification tag", because it is the format already used in the author's other projects, and IDs give traceability between criteria and tests.

The other options were rejected for these reasons:

* EARS is more formal, but brings nothing at this scale and would break consistency across projects.
* Checklists without IDs lose traceability.

### Consequences

* Good, because each test cites the criteria it covers, and uncovered criteria are easy to spot.
* Bad, because criteria must be maintained along with the specification. IDs are never reused or renumbered.
