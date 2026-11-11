---
status: accepted
date: 2026-11-11
---

# Use httpx2 and its mock transport

## Context and Problem Statement

FastMCP 4 and MCP SDK 2 depend on `httpx2`, the Pydantic-maintained continuation of `httpx`, not on `httpx`. `respx` only mocks `httpx`. Which HTTP client and mocking approach should the project use?

## Considered Options

* `httpx2` with its built-in `MockTransport`
* `httpx` with `respx`

## Decision Outcome

Chosen option: "`httpx2` with its built-in `MockTransport`", because it is the HTTP stack already installed through FastMCP, and it needs no extra mocking library.

### Consequences

* Good, because there is one HTTP stack and one dependency fewer.
* Bad, because tests build mock handlers themselves instead of using `respx`'s route helpers.
