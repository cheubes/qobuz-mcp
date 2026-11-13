---
status: accepted
date: 2026-11-13
---

# Check shell scripts with ShellCheck

## Context and Problem Statement

The shell scripts of ADR-0037 have no unit tests. Quoting mistakes, unset variables and non-portable constructs are common in shell and go unnoticed until a script runs on someone else's machine. How should the scripts be checked, locally and in CI?

## Considered Options

* ShellCheck, run with `uvx` from the `shellcheck-py` package at a pinned version, as a step of the existing `lint` job and in `check.sh`
* The ShellCheck preinstalled on the GitHub runner
* A dedicated ShellCheck action
* A separate `shellcheck` CI job

## Decision Outcome

Chosen option: "ShellCheck with `uvx` at a pinned version, in the `lint` job and in `check.sh`", because the same version runs locally and in CI, it follows the pattern already used for zizmor (ADR-0020), and no new action or required check is added.

The other options were rejected for these reasons:

* The preinstalled ShellCheck changes with the runner image, and is not installed on contributors' machines.
* A dedicated action is one more third-party action to pin and update, for a single command.
* A separate job would have to be added to the required checks of the `main` ruleset, a repository setting change, while static analysis of shell scripts belongs with the other linters.

### Consequences

* Good, because every script is checked before it reaches `main`, with the same version locally and in CI.
* Bad, because the pinned version is updated by hand: Dependabot does not track versions written in commands.
