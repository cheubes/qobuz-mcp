---
status: accepted
date: 2026-11-11
---

# Target Python 3.14

## Context and Problem Statement

Which Python version should the project require?

## Considered Options

* Python 3.13
* Python 3.14
* Python 3.15 (released October 2026)

## Decision Outcome

Chosen option: "Python 3.14", because it has a year of bug-fix releases and full ecosystem support.

The other options were rejected for these reasons:

* Python 3.13 is behind for no benefit.
* Python 3.15 is a month old. FastMCP still pulls a release-candidate dependency specifically for it.

### Consequences

* Good, because the project uses a mature, supported version until 2030.
* Bad, because moving to 3.15 later will need a new decision.
