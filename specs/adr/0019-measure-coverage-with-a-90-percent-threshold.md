---
status: accepted
date: 2026-11-11
---

# Measure coverage with a 90% threshold

## Context and Problem Statement

Traceability shows that every acceptance criterion has a test, but not which code no test exercises. Should the project measure coverage, and how?

## Considered Options

* `coverage` with branch coverage and `fail_under = 90`
* `pytest-cov`
* No coverage measurement

## Decision Outcome

Chosen option: "`coverage` with branch coverage and `fail_under = 90`", because it is the underlying tool, needs no pytest plugin, and a threshold makes untested code fail CI.

### Consequences

* Good, because untested code paths, such as error branches, are visible and bounded.
* Bad, because a threshold can push toward low-value tests. 90% leaves room for code that is not worth testing.
