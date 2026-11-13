---
status: accepted
date: 2026-11-13
---

# Provide shell scripts for multi-step tasks

## Context and Problem Statement

Installing the server takes several commands: `uv sync`, `qobuz-mcp login`, `claude mcp add` in user scope, and an edit of the Claude Desktop configuration with absolute paths. Updating takes `git pull` and `uv sync`, and checking that Qobuz did not change its API takes the live tests. Before a commit, contributors run five checks in a set order. Which of these should be wrapped in scripts, and how?

## Considered Options

* Three POSIX shell scripts in `scripts/` for the multi-step tasks: `install.sh`, `update.sh`, `check.sh`
* One script per CLI command (`login.sh`, `logout.sh`, `serve.sh`)
* A `Makefile`
* New Python subcommands, such as `qobuz-mcp setup`

## Decision Outcome

Chosen option: "Three POSIX shell scripts for the multi-step tasks", because a script only helps when it chains steps, and shell is the natural layer for driving `git`, `uv` and `claude`.

* `install.sh` checks macOS and uv, runs `uv sync`, runs `login` when no credentials are stored, registers the server in Claude Code in user scope when `claude` is available and the server is not registered yet, and prints the Claude Desktop configuration block with the actual paths. It skips completed steps, so it can run again.
* `install.sh` prints the Claude Desktop block instead of editing `claude_desktop_config.json`: the file holds the user's other servers, and a one-time paste does not justify the risk of damaging it.
* `update.sh` runs `git pull --ff-only` and `uv sync`, and with `--check` the live tests.
* `check.sh` runs every local check in the order of CI and stops at the first failure, live tests included.

The other options were rejected for these reasons:

* One script per command duplicates the CLI: `uv run qobuz-mcp login` is already one line, and two entry points would have to stay in sync.
* A `Makefile` gives one entry point, but conditional steps (already logged in, already registered) are awkward to write in make, which is meant for builds.
* Python subcommands would be tested and typed, but `update` cannot live in the code it updates, and driving `git` and `claude` from Python adds code for little gain.

### Consequences

* Good, because installation, update and checks each take one command, and the documented command lists point to the scripts.
* Good, because `check.sh` replaces the command lists of `CONTRIBUTING.md` and `CLAUDE.md`, which could drift from CI.
* Bad, because shell scripts have no unit tests: ShellCheck in CI is their only automated check (ADR-0038).
