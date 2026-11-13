---
status: accepted
date: 2026-11-13
---

# Support Antigravity CLI as a client

## Context and Problem Statement

The README and the install script cover Claude Desktop and Claude Code. The maintainer also uses Google's tools. The Gemini app cannot start a local stdio server. Gemini CLI can, but since June 18, 2026, Google no longer serves it to individual accounts (Gemini Code Assist for individuals, Google AI Pro and Ultra), which now get "This client is no longer supported" at sign-in. Its replacement for them is Antigravity CLI (`agy`). Antigravity CLI 1.5.8, installed with the official Homebrew cask, registers stdio servers with `agy mcp add` in its global configuration, `~/.gemini/config/mcp_config.json`. By default, it asks for the user's approval before running a tool of a configured MCP server. Should Antigravity CLI become a supported client, and how?

## Considered Options

* Support Antigravity CLI: README, install script registration with `agy mcp add`, manual checks
* Support Gemini CLI, limited to paid API keys and business licenses
* Do not support Google clients

## Decision Outcome

Chosen option: "Support Antigravity CLI", because it is the Google client that works with an individual account, it registers servers from the command line, and a client is only supported once its setup and its confirmation of write tools have been checked by hand.

* `scripts/install.sh` registers the server with `agy mcp add` when `agy` is available and `agy mcp list` has no `qobuz` server yet. `agy mcp add` has no scope: it writes the global configuration, active in every conversation. `--` separates its own flags from the arguments of `uv`, which start with `-`.
* The server is never combined with `--dangerously-skip-permissions` or `"toolPermission": "always-proceed"`, which skip approvals and remove the main safeguard against injected instructions (ADR-0025).
* The Gemini app stays unsupported: it cannot run a local server.

The other options were rejected for these reasons:

* Gemini CLI no longer works with an individual account: the maintainer could not run the manual checks, and the project would support a client Google retired for its users.
* Not supporting Google clients ignores clients the maintainer uses, at a small cost.

### Consequences

* Good, because the server works in a third client, registered by the install script without manual editing.
* Bad, because Antigravity CLI's approval behavior is outside the project's control, and its documentation does not say how every execution mode treats MCP tools: the manual checks confirm the default behavior, and must be repeated on each major change.
