---
status: accepted
date: 2026-11-10
---

# Guard writes with tool annotations and client confirmation

## Context and Problem Statement

Some write tools cannot be undone, such as deleting a playlist or removing favorites. Who confirms them?

## Considered Options

* MCP tool annotations (`readOnlyHint`, `destructiveHint`) and the MCP client's own per-call confirmation
* A mandatory `confirm: true` parameter
* The first option, with playlist deletion excluded from the scope

## Decision Outcome

Chosen option: "MCP tool annotations and client confirmation", because clients already ask before each tool call, and annotations let the user allowlist read tools once while keeping confirmation for writes.

The other options were rejected for these reasons:

* A `confirm` parameter is filled in by the model itself, so it protects nothing.
* Excluding deletion removes a feature for a risk that client confirmation already covers.

### Consequences

* Good, because nothing is reinvented and the user never confirms twice.
* Bad, because if the user allowlists write tools or runs the client in an auto-approve mode, no confirmation remains.
