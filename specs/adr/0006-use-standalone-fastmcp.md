---
status: accepted
date: 2026-11-11
---

# Use standalone FastMCP

## Context and Problem Statement

Since MCP Python SDK 2.0 (July 2026), the SDK's bundled `FastMCP` class is named `MCPServer`. "FastMCP" now refers only to the standalone `fastmcp` package. Which framework should the server use?

## Considered Options

* Standalone FastMCP (`fastmcp` 4.x, built on the official SDK)
* Official SDK `mcp` 2.x with `MCPServer`

## Decision Outcome

Chosen option: "Standalone FastMCP", because its in-memory client tests tools without stdio, and `fastmcp dev` opens the MCP Inspector for manual checks.

### Consequences

* Good, because it gives a better testing and development experience.
* Bad, because it brings a larger dependency tree (OAuth, proxies, OpenAPI generation) that this project does not use.
