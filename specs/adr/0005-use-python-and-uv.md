---
status: accepted
date: 2026-11-10
---

# Use Python and uv

## Context and Problem Statement

Which language and toolchain should the server be written in?

## Considered Options

* TypeScript with the official MCP SDK
* Python with FastMCP, managed with uv
* Swift
* Rust with the official `rmcp` SDK
* Go with the official SDK
* C

## Decision Outcome

Chosen option: "Python with FastMCP, managed with uv", because FastMCP's decorators keep tool declarations very concise, and Python and uv are familiar, modern tools.

The other options were rejected for these reasons:

* TypeScript has the reference SDK and matches kud/mcp-qobuz, but was not preferred.
* Swift has a less mature MCP SDK and heavier tooling for a small server.
* Rust gives a single fast binary, but means much more code for an HTTP relay.
* Go is a good native binary compromise, but brings nothing decisive here.
* C has no SDK and no memory safety, while handling network data and credentials.

### Consequences

* Good, because the code stays small and readable.
* Bad, because knowledge from kud/mcp-qobuz must be transposed from TypeScript.
* Bad, because uv must be installed (Homebrew). The system Python (3.9) is too old.
