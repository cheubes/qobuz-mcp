# qobuz-mcp

Local MCP server for macOS that lets an AI assistant (Claude Desktop, Claude Code, Antigravity CLI) explore the Qobuz catalog and manage the user's Qobuz library: favorites and playlists. Built in Python with FastMCP and uv, on top of Qobuz's unofficial web player API.

## Specifications

`specs/` is the source of truth for every design decision. Before writing or changing code, read the specification files relevant to the task.

- **`functional-specifications.md`**: purpose, constraints, scope and out of scope, setup flow (login, logout, client registration), tool catalog with MCP annotations, behaviors (results, errors, confidentiality, untrusted content, server instructions), acceptance criteria, open questions.
- **`technical-specifications.md`**: stack, project layout, project configuration (pyproject, ruff, mypy, coverage, pytest), CLI, credential storage, `app_id` extraction, API client and error mapping, endpoint mapping, MCP server rules, output models, development commands, client configuration, tests and traceability, continuous integration, publication (files and repository settings).
- **`adr/`**: architecture decision records, one file per decision (`NNNN-title-in-kebab-case.md`), in MADR 4 format. They explain why the specifications are what they are, and which alternatives were rejected.

`implementation-plan.md` defines the build order and tracks progress. It is not a specification: it refers to the specifications and never adds to them. Each step lists the acceptance criteria it delivers and its exit condition. A step is checked only when its exit condition holds. `scripts/check_traceability.py` parses this format, so it is kept as is (ADR-0026).

Specifications are `draft` until the "Output models" plan step is done, then `approved`. No production code is written before approval (ADR-0027). After approval, they keep evolving through the rules below, and their status stays `approved`.

## Decision records

- **Before reopening a settled question**, read the relevant ADR: the alternative being considered may already have been rejected, with its reason.
- **Every new design decision** (scope, dependency, architecture, convention, safeguard) gets a new ADR, written when the decision is made, along with the specification update it implies.
- **ADRs are immutable once accepted.** To revise a decision, write a new ADR and set the old one's status to `superseded by ADR-NNNN`. Only that status line changes in the old file.
- **Numbers are sequential and never reused.**

## Working with the specifications

- **Files reference each other** ("see `X.md`") instead of duplicating information. Follow the references rather than guessing: the referenced file is the source of truth.
- **When a specification changes**, search the other files that reference it (`grep` the file name and the section in `specs/`) and check they remain consistent.
- **When the specifications are silent or ambiguous** on a point needed for implementation, ask rather than assume: these are design choices, not free implementation details.
- **When code and specifications contradict each other**, the specification wins. If implementation shows a specification must change, update it and explain why, rather than silently diverging in code.
- **Open questions** in `functional-specifications.md` are resolved by updating the specifications, then removing the question.
- **Acceptance criteria** in `functional-specifications.md` are the verification contract. `[test]` and `[live]` criteria are covered by tests that cite their ID; `[manual]` criteria are checked by hand before the related plan step is marked done. Criterion IDs are never reused or renumbered.

## Commands

The reference list is "Development commands" in `technical-specifications.md`. The most common:

```sh
scripts/check.sh                 # every check of CI, in order, plus live tests
scripts/install.sh               # dependencies, login, client registration
scripts/update.sh [--check]      # pull, sync, optionally run the live tests
uv sync                          # install dependencies
uv run qobuz-mcp login           # store credentials in the Keychain
uv run qobuz-mcp serve           # run the server on stdio
uv run pytest                    # all tests, live tests included
uv run pytest -m "not live"      # without network
uv run ruff check . && uv run ruff format --check . && uv run mypy
uv run python scripts/check_traceability.py
```

## Working against the real Qobuz account

The credentials in the Keychain belong to the user's real Qobuz account, and the API is unofficial.

- Never call a write endpoint against the real account (scripts, manual tests, MCP Inspector) without explicit approval for that specific call. Live tests are read-only and must stay so.
- Never display, log or commit a token, an authorization code, a password or the content of the Keychain item.
- Test fixtures are synthetic (ADR-0023). Never save a real API response, the web player HTML or bundle, a real `app_id` or any account data in the repository.
- Exploration and proof-of-concept scripts live outside the repository.

## Before each commit

- **Run `scripts/check.sh`: lint, format check, ShellCheck, type check, the full test suite (live tests included) and the traceability check.** If live tests fail, report it: it may mean Qobuz changed its API. CI runs the same checks except live tests (ADR-0018), so a local run is the only one that catches API drift.
- **Check all files in `specs/`** for consistency, not only those touched by the commit.
- **If one or more specifications need adjusting** (to stay consistent with each other or with the change), block the commit: propose the updates and wait for approval before applying them, then commit.
- **Update `specs/implementation-plan.md`**: check a step only when its exit condition holds.
- **Check `README.md` at every commit**: its status matches the implementation plan, its scope matches the functional specifications, and its disclaimers match "Publication" in the technical specifications.
- **Check the other documents when the commit touches what they restate**: `CONTRIBUTING.md` and this file when commands or the contribution process change, `SECURITY.md` when credential handling or writes change, `.github/` templates when the contribution process changes.
- **When one of these documents restates the specifications, the specifications win**: fix the document. If the gap reveals an error in the specifications, follow the usual process to change them instead.

## Pull requests

Changes reach `main` through pull requests (ADR-0030).

- **One branch per plan step or self-contained change.** The pull request title follows Conventional Commits: it becomes the squash commit message.
- **The pull request body** gives the context, the notable changes, the acceptance criteria delivered and a test plan.
- **Wait for CI and CodeQL to pass**, then give the maintainer the link and a short summary.
- **Merge only after the maintainer's explicit approval of that pull request**, with `gh pr merge --squash`. Approval of one pull request never extends to the next.
- **The admin bypass of the `main` ruleset** is for emergencies only, each time with the maintainer's explicit approval.

## Conventions

- Everything is in English: code, specifications, `README.md`, this file.
- Python code follows PEP 8 naming, enforced by ruff. Documentation files use kebab-case names.
- stdout carries the MCP protocol: server code never writes to it. Diagnostics go through `logging`, to stderr.
- Text returned by Qobuz (names, descriptions, editorial texts) is untrusted third-party content (ADR-0025). It is returned as data, and never interpolated into the server instructions or tool descriptions.
- Tool docstrings and parameter descriptions are what the model reads to choose and call a tool: write them for the model, consistent with the functional specification.
- A new tool is first added to the tool catalog in `functional-specifications.md`, with its annotation, then to the endpoint mapping in `technical-specifications.md`, before any code.
- Any new dependency is discussed before being added, recorded in an ADR, then listed in the stack section of `technical-specifications.md`.
- Dependencies are managed with uv only (`uv add`, `uv add --dev`, `uv remove`), never with pip or by editing `pyproject.toml` dependency lists or `uv.lock` by hand.
