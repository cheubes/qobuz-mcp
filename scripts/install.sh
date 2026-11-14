#!/bin/sh
# Install qobuz-mcp: dependencies, Qobuz login, Claude Code and Antigravity CLI registration,
# Claude Desktop configuration. Safe to run again: completed steps are skipped, and the
# Antigravity CLI registration is updated.
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

echo "==> Antigravity CLI"
agy_failed=false
if ! command -v agy >/dev/null 2>&1; then
  echo "Antigravity CLI not found: skipped."
# `add` adds or updates, so a moved clone gets its new path, and `enable` undoes a disable.
# The Antigravity app does not inherit the shell PATH, hence the absolute path to uv.
elif agy mcp add qobuz -- "$uv_path" run --directory "$repo" qobuz-mcp serve \
  && agy mcp enable qobuz; then
  echo "Add the ask rules of the write tools with /permissions: see README, Client configuration."
else
  echo "Antigravity CLI registration failed: see the error above." >&2
  agy_failed=true
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

if [ "$agy_failed" = true ]; then
  exit 1
fi
