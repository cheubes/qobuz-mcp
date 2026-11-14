---
status: accepted
date: 2026-11-14
---

# Pin write confirmation in Antigravity

## Context and Problem Statement

ADR-0039 supports Antigravity CLI, registered with `agy mcp add`, and relies on its default behavior: asking the user's approval before running a tool of a configured MCP server. Two facts, found after that decision, weaken it:

* `agy mcp add` writes `~/.gemini/config/mcp_config.json`, which the Antigravity desktop app also reads: the maintainer's app loaded the qobuz server and cached the schemas of its tools. Registering the server for the CLI exposes it to the app, which no criterion covers.
* Since Antigravity CLI 1.5.7, sessions start in Auto mode by default. Its changelog describes how Auto reviews commands and file edits, not how it treats MCP tools: the confirmation of write tools rests on undocumented behavior.

Antigravity CLI 1.5.8 applies permission rules to every MCP tool: an `mcp(<server>/<tool>)` rule set to `ask` makes that tool ask for approval, and the `Tool Permission` setting `strict` takes precedence over Auto mode. Rules are global, stored in the shared configuration directory. No `agy` subcommand writes them: they are added with `/permissions` in a session. How should the server keep the confirmation of write tools in Antigravity?

## Considered Options

* Support the desktop app too, and document an `ask` rule for each write tool
* Recommend the `strict` tool permission
* Keep relying on the default behavior, checked by hand at each version

## Decision Outcome

Chosen option: "Support the desktop app too, and document an `ask` rule for each write tool", because a rule per write tool pins their confirmation whatever the agent mode, without slowing down the user's other work, and the registration cannot reach the CLI without reaching the app.

* The README tells the user to add, with `/permissions`, an `ask` rule for each write tool of FS 5.3, and to allow read-only tools one by one with an `allow` rule, never the whole server.
* The README no longer states that Antigravity asks for approval by default.
* The Antigravity desktop app is a supported client. Manual criteria check that it lists the tools, and that the CLI in Auto mode and the app ask before each write tool, with the documented rules.
* `scripts/install.sh` reminds the user to add the rules after registering the server, since it cannot write them.
* The rest of ADR-0039 stands.

The other options were rejected for these reasons:

* `strict` asks for approval of every file edit and command in every session, beyond the qobuz server.
* The default behavior of Auto mode for MCP tools is not documented, so a version could change it without notice.

### Consequences

* Good, because the confirmation of write tools no longer depends on the agent mode.
* Bad, because the user adds ten rules by hand, and a write tool added later needs its own rule, which the README must list.
* Bad, because `--dangerously-skip-permissions` still bypasses every rule: the README keeps forbidding it with this server.
