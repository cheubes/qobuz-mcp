# qobuz-mcp

A local MCP server for macOS that lets an AI assistant, such as Claude Desktop or Claude Code, explore the Qobuz catalog and manage your Qobuz library: favorites and playlists.

> **Status: in development, not usable yet.** The specifications are approved and the project scaffold and CI are in place. The server itself is being built step by step, following the [implementation plan](specs/implementation-plan.md).

## What it will do

- Search and browse the catalog: albums, artists, tracks, playlists, labels, genres.
- Browse editorial content: new releases, press awards, best sellers, editorial playlists.
- Read your library: favorites, playlists you own or follow, purchases.
- Change your library: add or remove favorites, create, edit, reorder and delete playlists, follow or unfollow playlists.

It will not control playback, and it will not download or stream audio.

## Disclaimers

- This project is not affiliated with, endorsed or sponsored by Qobuz. "Qobuz" is a trademark of its owner, used here only to indicate compatibility.
- It relies on Qobuz's unofficial web player API, outside Qobuz's terms of service. It may break at any time.
- It is intended for strictly personal use of your own account.
- It comes with no guarantee of any kind. You bear the risks of using it with your account.
- Write tools rely on your MCP client asking you to confirm each call. If you allowlist them, or use an auto-approve mode, you remove the main safeguard against instructions hidden in third-party content, such as a playlist description asking the assistant to delete your playlists.

## How it is built

The project is specification-driven. Everything starts in [`specs/`](specs/):

- [Functional specifications](specs/functional-specifications.md): scope, tools, behaviors and acceptance criteria.
- [Technical specifications](specs/technical-specifications.md): stack, architecture, API usage, tests, CI.
- [Architecture decision records](specs/adr/): why things are the way they are, and which alternatives were rejected.
- [Implementation plan](specs/implementation-plan.md): build order and progress. CI checks that every acceptance criterion of a completed step is covered by a test.

Development is assisted by Claude Code, following the project rules in [`CLAUDE.md`](CLAUDE.md).

## Contributing and security

Contributions start with an issue: see [CONTRIBUTING.md](CONTRIBUTING.md). To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

[CC0 1.0 Universal](LICENSE): the code is dedicated to the public domain.
