---
status: accepted
date: 2026-11-11
---

# Run CI on GitHub Actions

## Context and Problem Statement

The repository is meant to become public soon. The pre-commit checks in `CLAUDE.md` only bind the assistant, not commits made without it. What should verify every change?

## Considered Options

* A complete GitHub Actions CI: lint, types, tests on macOS, traceability, build, internal links, secrets, workflow audit
* A minimal GitHub Actions CI: lint, types and tests on Linux
* Local git hooks with the `pre-commit` framework
* No CI, only the rules in `CLAUDE.md`

## Decision Outcome

Chosen option: "A complete GitHub Actions CI", because a public repository gets unlimited standard runner minutes, including macOS, and a complete CI checks every commit and pull request whoever makes it.

The other options were rejected for these reasons:

* A minimal CI misses the traceability, secrets and supply chain checks a public repository needs.
* Local hooks would add a dependency, and the live tests would make every commit slow.
* No CI leaves commits made without the assistant unchecked.

The main choices within the CI:

* Tests run on macOS, the target platform. Python 3.15 runs as a non-blocking early warning.
* Lint, types, traceability, build, links, secrets and workflow audit run on Linux, which is faster.
* A traceability script checks that every `[test]` and `[live]` acceptance criterion is cited by a test.

### Consequences

* Good, because every change is checked the same way, including `uv.lock` freshness and spec-to-test traceability.
* Bad, because the CI has more jobs to maintain. The Python 3.15 and `links` jobs are the first candidates to drop if it becomes a burden.
