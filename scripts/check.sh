#!/bin/sh
# Run every local check, in the order of CI, and stop at the first failure. Unlike CI, the live
# tests run too: they are skipped when no Qobuz credentials are stored.
set -eu
cd "$(dirname "$0")/.."

uv lock --check
uv run ruff check .
uv run ruff format --check .
uvx --from shellcheck-py@0.11.0.1 shellcheck scripts/*.sh
uv run mypy
uv run coverage run -m pytest -m "not live"
uv run coverage report
uv run pytest -m live
uv run python scripts/check_traceability.py
