---
status: accepted
date: 2026-11-13
---

# Support Gemini CLI as a client

## Context and Problem Statement

The README and the install script cover Claude Desktop and Claude Code. The maintainer also uses Google's Gemini. The Gemini app (web and mobile) cannot start a local stdio server, but Gemini CLI can: it reads MCP servers from `~/.gemini/settings.json` and registers them with `gemini mcp add`. Gemini CLI 0.68.0 connected to the server during a test. Should Gemini CLI become a supported client, and how?

## Considered Options

* Support Gemini CLI: README, install script registration in user scope, manual checks
* Document Gemini CLI in the README only, without the install script or manual checks
* Do not support Gemini

## Decision Outcome

Chosen option: "Support Gemini CLI", because it runs the server like Claude Code does, and a client is only supported once its setup and its confirmation of write tools have been checked by hand.

* `scripts/install.sh` registers the server with `gemini mcp add --scope user` when `gemini` is available and `~/.gemini/settings.json` has no `qobuz` server yet. The user scope makes the server available in every directory; the default project scope writes into the current directory and requires a trusted workspace.
* The server is never registered with `--trust`, which bypasses every tool call confirmation and removes the main safeguard against injected instructions (ADR-0025).
* The Gemini app stays unsupported: it cannot run a local server.

The other options were rejected for these reasons:

* Documentation alone would leave a client unchecked, while the README presents it as working.
* Not supporting Gemini ignores a client the maintainer uses, at a small cost.

### Consequences

* Good, because the server works in a third client, with one install command.
* Bad, because Gemini CLI's confirmation behavior is outside the project's control, like that of the Claude clients, and must be checked by hand on each major change.
