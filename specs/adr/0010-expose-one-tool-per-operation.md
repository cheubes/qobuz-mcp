---
status: accepted
date: 2026-11-10
---

# Expose one tool per operation

## Context and Problem Statement

Operations could be exposed as one tool each, or grouped into a few tools with an `action` parameter (for example `manage_favorites(action=...)`).

## Considered Options

* One tool per operation
* Grouped tools with an `action` parameter

## Decision Outcome

Chosen option: "One tool per operation", because MCP annotations apply to a whole tool. A grouped tool mixing reads and writes could not be marked read-only, which would defeat ADR-0009.

### Consequences

* Good, because each tool has a precise annotation, schema and description.
* Bad, because there are many tools (23), which costs context in the client.
