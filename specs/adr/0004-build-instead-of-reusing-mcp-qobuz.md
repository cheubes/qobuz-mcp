---
status: accepted
date: 2026-11-10
---

# Build a new server instead of reusing kud/mcp-qobuz

## Context and Problem Statement

`kud/mcp-qobuz` (TypeScript, MIT, created June 2026, single maintainer) already covers search, detail lookups, library reading, playlist creation, adding tracks and editing descriptions. It lacks favorite writes, track removal and reordering, playlist deletion, purchases and editorial content, and relies on `qobuz-cli` for login. Should this project build, fork or reuse it?

## Considered Options

* Build a new server, using kud/mcp-qobuz as a reference for the API
* Fork kud/mcp-qobuz and add what is missing
* Use kud/mcp-qobuz as is and contribute upstream

## Decision Outcome

Chosen option: "Build a new server", because the gaps in the target scope are large (mostly writes), the project depends on a single maintainer, and owning the server leaves authentication, tool design and safeguards under this project's control.

### Consequences

* Good, because every design choice is made for this scope.
* Good, because its MIT license allows learning from its API usage.
* Bad, because it means more work than a fork.
