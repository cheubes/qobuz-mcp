#!/bin/sh
# Update qobuz-mcp to the latest version of its branch. With --check, also run the live tests,
# which tell whether Qobuz changed its API.
set -eu
cd "$(dirname "$0")/.."

check=false
case "${1:-}" in
  "") ;;
  --check) check=true ;;
  *)
    echo "Usage: scripts/update.sh [--check]" >&2
    exit 2
    ;;
esac

echo "==> Updating the code"
git pull --ff-only

echo "==> Updating dependencies"
uv sync

if [ "$check" = true ]; then
  echo "==> Checking the Qobuz API with the live tests"
  uv run pytest -m live
fi

echo "Done. Restart Claude Desktop, and open a new Claude Code or Gemini CLI session, to use the new version."
