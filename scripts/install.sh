#!/bin/sh
# Install qobuz-mcp: dependencies, Qobuz login, Claude Code registration, Claude Desktop
# configuration. Safe to run again: completed steps are skipped.
set -eu
cd "$(dirname "$0")/.."
repo=$(pwd)

if [ "$(uname -s)" != "Darwin" ]; then
  echo "qobuz-mcp runs on macOS only: it stores its credentials in the macOS Keychain." >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required: install it with 'brew install uv', then run this script again." >&2
  exit 1
fi
uv_path=$(command -v uv)

echo "==> Installing dependencies"
uv sync

echo "==> Qobuz login"
# Without -w or -g, `security` checks the Keychain item exists without reading the token.
if security find-generic-password -s qobuz-mcp -a default >/dev/null 2>&1; then
  echo "Already logged in. Run 'uv run qobuz-mcp login' to log in again."
else
  uv run qobuz-mcp login
fi

echo "==> Claude Code"
if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code not found: skipped."
elif claude mcp get qobuz >/dev/null 2>&1; then
  echo "The qobuz server is already registered."
else
  claude mcp add --scope user qobuz -- uv run --directory "$repo" qobuz-mcp serve
fi

echo "==> Claude Desktop"
desktop_config="$HOME/Library/Application Support/Claude/claude_desktop_config.json"
if [ -f "$desktop_config" ] && grep -q '"qobuz"' "$desktop_config"; then
  echo "The Claude Desktop configuration already has a qobuz server."
else
  cat <<CONFIG
Add this server to $desktop_config,
inside "mcpServers", then restart Claude Desktop:

    "qobuz": {
      "command": "$uv_path",
      "args": ["run", "--directory", "$repo", "qobuz-mcp", "serve"]
    }
CONFIG
fi
