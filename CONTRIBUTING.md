# Contributing

Thanks for your interest. This is a personal project with a single maintainer, built on an unofficial API that can change at any time. These rules keep contributions useful and reviewable.

## Start with an issue

- Open an issue first, using the bug report or feature request form.
- A pull request is accepted only when it is linked to an issue the maintainer has approved. Unsolicited pull requests may be closed without review.
- Playback control and audio downloads are out of scope.

## Specifications first, then code

The project is specification-driven. A change follows this order:

1. Update the specifications in [`specs/`](specs/): the [functional specifications](specs/functional-specifications.md) for behavior and tools, the [technical specifications](specs/technical-specifications.md) for implementation.
2. Record any design decision as a new [ADR](specs/adr/), in MADR 4 format. Accepted ADRs are never edited: a revised decision gets a new ADR, and the old one is marked `superseded by ADR-NNNN`.
3. Add or update the acceptance criteria, with their tag (`[test]`, `[live]` or `[manual]`), and assign each to a step of the [implementation plan](specs/implementation-plan.md).
4. Write the code and its tests. Each test cites, in its docstring, the acceptance criterion IDs it covers.

[`CLAUDE.md`](CLAUDE.md) holds the full project rules. They apply to human contributors as well.

## Local checks

You need macOS, [uv](https://docs.astral.sh/uv/) and, for live tests, a Qobuz account. Run before opening a pull request:

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
uv run python scripts/check_traceability.py
```

`uv run pytest` includes live tests against the real Qobuz API when you are logged in (`uv run qobuz-mcp login`). They are read-only. Use `uv run pytest -m "not live"` to skip them. CI runs every check except live tests.

## Rules that are not negotiable

- Never include a token, an authorization code, a password or any account data in code, tests, issues or pull requests.
- Test fixtures are synthetic. Never commit a real API response or a file from the Qobuz web player.
- Live tests never call a write endpoint.
- Dependencies are managed with uv only (`uv add`, `uv remove`). A new dependency is discussed in its issue first, then recorded in an ADR.

## Commits and pull requests

- Commit messages and pull request titles follow [Conventional Commits](https://www.conventionalcommits.org/), in English.
- Pull requests are squash-merged, so the pull request title becomes the commit message.
- Everything is in English: code, comments, specifications, documentation.
