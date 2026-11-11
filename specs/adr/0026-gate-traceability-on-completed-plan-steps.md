---
status: accepted
date: 2026-11-11
---

# Gate traceability on completed plan steps

## Context and Problem Statement

The traceability check requires every `[test]` and `[live]` acceptance criterion to be cited by a test. CI arrives before any feature, so the check would fail from the start and block every pull request. The implementation plan also had no progress tracking and no link to the criteria. How should the plan track progress, and when should a criterion be required?

## Considered Options

* Plan steps with checkboxes, each listing the criteria it delivers and its exit condition. The check requires only the criteria of checked steps
* A status field on each criterion in the functional specifications
* Disabling the traceability job until the first features exist

## Decision Outcome

Chosen option: "Plan steps with checkboxes and delivered criteria", because it keeps the functional specifications free of progress data, makes the plan the single place that tracks progress, and keeps the check active from the first CI run.

The other options were rejected for these reasons:

* A status per criterion would mix progress into the specification.
* Disabling the job means remembering to turn it back on.

The check also verifies that each criterion is delivered by exactly one step, so no criterion is forgotten in the plan.

This decision refines ADR-0017, whose traceability check required every criterion from the start.

### Consequences

* Good, because progress, criteria and tests are linked and checked automatically.
* Bad, because the plan's format becomes a contract the script parses. Format changes must be made in both places.
