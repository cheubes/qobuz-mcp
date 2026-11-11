---
status: accepted
date: 2026-11-11
---

# Merge changes through reviewed pull requests

## Context and Problem Statement

The repository is public and `main` has a ruleset requiring pull requests and passing checks, with an admin bypass. Until publication, the assistant committed and pushed directly to `main`. With feature code starting, how should changes reach `main`, and who merges them?

## Considered Options

* Pull requests opened by the assistant, merged by the assistant after passing checks and the maintainer's explicit approval of each pull request
* Pull requests opened by the assistant, merged by the maintainer on GitHub
* Pull requests merged by the assistant as soon as checks pass
* Direct pushes to `main` through the admin bypass

## Decision Outcome

Chosen option: "Merged by the assistant after passing checks and the maintainer's explicit approval", because CI runs before anything reaches `main`, the maintainer approves every change, and work continues without switching to the GitHub interface.

The other options were rejected for these reasons:

* Merging on GitHub works, but the assistant cannot tell when to continue.
* Merging as soon as checks pass leaves no human review, too risky for code handling credentials.
* Direct pushes skip CI until after the fact, and contradict the discipline asked of contributors.

### Consequences

* Good, because every change is checked by CI and approved by the maintainer before reaching `main`.
* Bad, because each change waits for the maintainer's approval.
