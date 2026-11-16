---
status: accepted
date: 2026-11-14
---

# Update the Antigravity registration at each install

## Context and Problem Statement

Under ADR-0039, `scripts/install.sh` registers the server with `agy mcp add` only when `agy mcp list` shows no `qobuz` server, found by matching the start of a line of its text table. Since the script runs with `set -eu`, a failing `agy` call stopped it before the Claude Desktop step. The registered command was a bare `uv`, while the Antigravity desktop app, which reads the same configuration (ADR-0045), does not inherit the shell `PATH`, the reason Claude Desktop gets an absolute path. Skipping an existing registration also left a stale path after the clone moved, and a server the user disabled with `agy mcp disable` counted as installed. `agy mcp add` adds or updates a server, and `agy mcp enable` enables it, both with exit status 0 when nothing changes. How should the install script register the server in Antigravity?

## Considered Options

* Run `agy mcp add` then `agy mcp enable` at each install, with the absolute path to `uv`
* Keep detecting an existing registration, and fix the detection and the path

## Decision Outcome

Chosen option: "Run `agy mcp add` then `agy mcp enable` at each install", because both commands are idempotent, and running them always fixes a stale path, a disabled server and a bare `uv` without parsing a text table whose format is not a contract.

* `scripts/install.sh` runs `agy mcp add qobuz -- <absolute path to uv> run --directory <repo> qobuz-mcp serve`, then `agy mcp enable qobuz`, whenever `agy` is available.
* If either fails, the script reports it, still runs the Claude Desktop step, and exits with a non-zero status.
* This refines the registration rule of ADR-0039; its other decisions stand.

The other option was rejected because it keeps a dependency on the text output of `agy mcp list`, which can change between versions, for no benefit over idempotent commands.

### Consequences

* Good, because each run of the install script repairs the Antigravity registration.
* Bad, because a hand-made change to the qobuz entry, such as an `--env QOBUZ_APP_ID=...` added with `agy mcp add`, is overwritten at the next install: the README says so.
* Bad, because `agy mcp enable` also succeeds for an unknown name, so it checks nothing on its own: `add` comes first.
