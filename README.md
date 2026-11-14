# qobuz-mcp

A local MCP server for macOS that lets an AI assistant, such as Claude Desktop, Claude Code, Antigravity CLI or the Antigravity app, explore the Qobuz catalog and manage your Qobuz library: favorites and playlists.

> **Status: usable.** Every step of the [implementation plan](specs/implementation-plan.md) is done, and the setup has been checked in Claude Desktop, Claude Code, Antigravity CLI and the Antigravity app. The server relies on an unofficial API: see the disclaimers below.

## What it does

- Search and browse the catalog: albums, artists, tracks, playlists, labels, genres.
- Recommend music: similar albums, radios from an album, an artist or a track, suggestions to extend a list of tracks.
- Browse editorial content: new releases, press awards, best sellers, album of the week, editorial playlists, awards, magazine stories.
- Read your library: favorites, playlists you own or follow, purchases, new releases from your favorite artists, and whether given items are in your library.
- Change your library: add or remove favorites, create, edit, reorder and delete playlists, follow or unfollow playlists.

It does not control playback, and it does not download or stream audio.

## Disclaimers

- This project is not affiliated with, endorsed or sponsored by Qobuz. "Qobuz" is a trademark of its owner, used here only to indicate compatibility.
- It relies on Qobuz's unofficial web player API, outside Qobuz's terms of service. It may break at any time.
- It is intended for strictly personal use of your own account.
- It comes with no guarantee of any kind. You bear the risks of using it with your account.
- Write tools rely on your MCP client asking you to confirm each call. If you allowlist them, or use an auto-approve mode, you remove the main safeguard against instructions hidden in third-party content, such as a playlist description asking the assistant to delete your playlists.

## Prerequisites

- macOS, since credentials are stored in the macOS Keychain.
- [Homebrew](https://brew.sh) and [uv](https://docs.astral.sh/uv/): `brew install uv`. uv installs the Python version the project needs.
- A Qobuz account.
- Claude Desktop, Claude Code or [Antigravity CLI](https://antigravity.google/product/antigravity-cli) (`brew install --cask antigravity-cli`), or another MCP client that supports the stdio transport. The Gemini app cannot run a local server, and Gemini CLI no longer serves individual accounts.

## Installation

```sh
git clone https://github.com/cheubes/qobuz-mcp.git
cd qobuz-mcp
scripts/install.sh
```

The script installs the dependencies, runs the login described below when no credentials are stored, registers the server in Claude Code and Antigravity CLI when they are installed, and prints the block to add to the Claude Desktop configuration, with your paths. It skips the steps already done, except the Antigravity CLI registration, which it updates, so you can run it again. The sections below detail each step, to do them by hand.

## Update

```sh
scripts/update.sh
```

The script pulls the latest version and updates the dependencies. Then restart Claude Desktop and the Antigravity app, and open a new Claude Code or Antigravity CLI session. With `--check`, it also runs the live tests, which tell whether Qobuz changed its API: run it when a tool starts failing.

## Login

```sh
uv run qobuz-mcp login
```

The command opens the Qobuz sign-in page in your browser, and prints its URL in case the browser does not open. Sign in on Qobuz's own page: the command never sees your password. Qobuz then redirects the browser to a temporary local address, and the command stores a token in the macOS Keychain. The sign-in must complete within 5 minutes.

If the browser sign-in does not work, copy a token by hand from the Qobuz web player:

1. Open [play.qobuz.com](https://play.qobuz.com) and sign in.
2. Open the browser's developer tools, on the Network tab, and reload the page.
3. Select any request to `www.qobuz.com/api.json/`, and copy the value of its `X-User-Auth-Token` request header.
4. Run `uv run qobuz-mcp login --token` and paste the token when prompted.

`uv run qobuz-mcp logout` removes the stored credentials. Login and logout apply to the next tool call, without restarting your MCP client.

The server identifies itself with the `app_id` of the Qobuz web player, read at login. If Qobuz rejects it, run `login` again. To force a value, set the `QOBUZ_APP_ID` environment variable in the server configuration.

Never share the token: it gives access to your Qobuz account.

## Client configuration

Replace `/path/to/qobuz-mcp` with the absolute path of your clone.

**Claude Code:**

```sh
claude mcp add --scope user qobuz -- uv run --directory /path/to/qobuz-mcp qobuz-mcp serve
```

`--scope user` makes the server available in every Claude Code session. Without it, the server is only registered for the directory where you ran the command.

**Claude Desktop:** add the server to `~/Library/Application Support/Claude/claude_desktop_config.json`, then restart Claude Desktop. Claude Desktop does not inherit your shell `PATH`, so `command` must be the absolute path to `uv`, as printed by `which uv` (`/opt/homebrew/bin/uv` on Apple silicon, `/usr/local/bin/uv` on Intel Macs):

```json
{
  "mcpServers": {
    "qobuz": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["run", "--directory", "/path/to/qobuz-mcp", "qobuz-mcp", "serve"]
    }
  }
}
```

**Antigravity CLI and the Antigravity app:**

```sh
agy mcp add qobuz -- /opt/homebrew/bin/uv run --directory /path/to/qobuz-mcp qobuz-mcp serve
```

The server goes to the global configuration, `~/.gemini/config/mcp_config.json`, which the Antigravity desktop app also reads: it is available in every conversation of both. As for Claude Desktop, the app does not inherit your shell `PATH`, hence the absolute path to `uv`. `scripts/install.sh` runs this command at each install, which overwrites any change you made to the qobuz entry, such as an `--env` variable.

Whether Antigravity asks before running a tool depends on its agent mode, and Auto mode, the default, does not document how it treats MCP tools. Make every write tool ask for your approval: in an Antigravity CLI session, run `/permissions` and add an `ask` rule for each of them:

```text
mcp(qobuz/add_favorites)
mcp(qobuz/remove_favorites)
mcp(qobuz/create_playlist)
mcp(qobuz/update_playlist)
mcp(qobuz/add_tracks_to_playlist)
mcp(qobuz/remove_tracks_from_playlist)
mcp(qobuz/move_playlist_tracks)
mcp(qobuz/delete_playlist)
mcp(qobuz/follow_playlist)
mcp(qobuz/unfollow_playlist)
```

The rules are global: they apply to the CLI and to the app. To stop confirming a read-only tool, add an `allow` rule for that tool only, such as `mcp(qobuz/search_catalog)`, never for the whole server. Never use `--dangerously-skip-permissions` or the `always-proceed` tool permission with this server: they bypass these rules and remove the confirmation of write tools.

In the other clients, read-only tools can be allowed once. Keep the confirmation of write tools: see the last disclaimer above.

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
