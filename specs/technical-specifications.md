# Technical specifications

Status: draft. Implements [functional-specifications.md](functional-specifications.md).

## 1. Stack

| Concern | Choice |
|---|---|
| Language | Python 3.14 (`requires-python = ">=3.14"`, pinned by `.python-version`) |
| Project and environment management | uv, installed with Homebrew. uv installs Python itself |
| Build backend | `uv_build` |
| MCP framework | FastMCP standalone (`fastmcp>=4.1,<5`) |
| HTTP client | `httpx2` (async) |
| Data models | `pydantic` v2 |
| Credential storage | `keyring` (macOS Keychain backend) |
| CLI | `argparse` and `getpass` (standard library) |
| Tests | `pytest`, anyio pytest plugin, `httpx2.MockTransport` |
| Lint and format | `ruff` |
| Type checking | `mypy`, strict mode, with the pydantic plugin |

Runtime dependencies: `fastmcp`, `httpx2`, `pydantic`, `keyring`. `httpx2` and `pydantic` also come with FastMCP, but the code imports them directly, so they are declared explicitly.

Development dependencies (`dev` group, PEP 735): `pytest`, `anyio`, `coverage`, `ruff`, `mypy`.

CI-only tools, not project dependencies: gitleaks, zizmor, lychee, CodeQL (section 14).

Prerequisites on the machine: Homebrew and uv. Node.js only for the MCP Inspector (section 11).

## 2. Project layout

```
.github/
    dependabot.yml
    ISSUE_TEMPLATE/
        bug_report.yml
        feature_request.yml
        config.yml
    pull_request_template.md
    workflows/
        ci.yml
        codeql.yml
.gitignore
.python-version
CLAUDE.md
CONTRIBUTING.md
LICENSE
README.md
SECURITY.md
pyproject.toml
uv.lock
scripts/
    check_traceability.py
src/qobuz_mcp/
    __init__.py
    __main__.py          # python -m qobuz_mcp
    cli.py               # serve, login, logout
    credentials.py       # Keychain read/write
    app_id.py            # app_id extraction from the web player
    api.py               # QobuzClient: HTTP calls, auth headers, error mapping
    errors.py            # exception hierarchy
    models.py            # pydantic output models and mapping from raw payloads
    server.py            # FastMCP instance, lifespan, tool registration
    tools/
        __init__.py
        catalog.py       # FS 5.1
        library.py       # FS 5.2 and favorites writes
        playlists.py     # playlist writes
tests/
    conftest.py
    memory_keyring.py    # in-memory keyring backend
    fixtures/            # synthetic API payloads and web player snippets
    unit/
    live/
```

## 3. Project configuration

All configuration lives in `pyproject.toml`.

- `[build-system]`: `uv_build`.
- `[project.scripts]`: one console script, `qobuz-mcp = "qobuz_mcp.cli:main"`.
- `[project]` declares `license = "CC0-1.0"`, matching `LICENSE`.
- `[dependency-groups]`: `dev` group (section 1).
- `[tool.uv]`: `required-version`, set at scaffold time to the current uv minor version (`>=0.13,<0.14` as of 0.13.7). `astral-sh/setup-uv` reads it, so CI and local runs use the same uv.
- `[tool.ruff]`: `line-length = 100`. Rule sets: `E`, `W`, `F`, `I` (imports), `N` (PEP 8 naming), `UP` (pyupgrade), `B` (bugbear), `SIM`, `ASYNC`, `RUF`. The target version is derived from `requires-python`.
- `[tool.mypy]`: `strict = true`, `plugins = ["pydantic.mypy"]`, applied to `src/`, `tests/` and `scripts/`.
- `[tool.coverage]`: `source = ["qobuz_mcp"]`, `branch = true`, `fail_under = 90`.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `addopts = ["--strict-markers"]`, marker `live` declared with its description.

Async tests use the anyio plugin (`@pytest.mark.anyio`), with the `anyio_backend` fixture fixed to `asyncio` in `tests/conftest.py`.

## 4. CLI

| Command | Behavior |
|---|---|
| `qobuz-mcp serve` | Starts the MCP server on stdio |
| `qobuz-mcp login` | Prompts for email (`input`) and password (`getpass`), extracts the `app_id`, calls `user/login`, stores credentials |
| `qobuz-mcp login --token` | Prompts for a token (`getpass`), extracts the `app_id`, validates the token with an authenticated call (section 8), stores credentials |
| `qobuz-mcp logout` | Deletes the Keychain entry |

`login` prints the account's display name on success and never echoes the token or password.

## 5. Credentials

- One Keychain item: service `qobuz-mcp`, account `default`.
- Value: JSON object `{"app_id": str, "user_auth_token": str, "user_id": int}`. `user_id` is kept only if an in-scope endpoint needs it (validated in the proof of concept).
- `QOBUZ_APP_ID`, when set, overrides the stored `app_id` at read time.
- The server reads the item at each tool call, with no in-memory cache. `login` and `logout` therefore take effect on the next call without restarting the client (FS-SETUP-2). A cache would keep using the token after `logout`, since logging out does not revoke the token on Qobuz's side.
- A missing item does not prevent the server from starting: tools return the "not logged in" error (FS-BEH-2) until the user logs in.

Known limitation: Keychain access is granted to the Python interpreter binary that created the item. When uv upgrades the interpreter, macOS asks again for Keychain access on the next run.

## 6. `app_id` extraction

1. `GET https://play.qobuz.com/login`.
2. Find the bundle URL in the HTML: pattern `/resources/<version>/bundle.js`.
3. `GET` the bundle.
4. Extract the production `app_id` with a regular expression on the bundle's config object.

The exact patterns are confirmed during the proof of concept (see [implementation-plan.md](implementation-plan.md)) and covered by a live test. Extraction failure raises `AppIdExtractionError`, whose message suggests setting `QOBUZ_APP_ID`.

## 7. Qobuz API client

`QobuzClient` wraps one shared `httpx2.AsyncClient`, created and closed in the FastMCP lifespan.

- Base URL: `https://www.qobuz.com/api.json/0.2/`.
- Headers on every call: `X-App-Id`, and `X-User-Auth-Token` for authenticated calls.
- Timeout: 15 seconds.
- `user/login` sends the credentials in a POST form body, never in the query string.
- One method per endpoint, returning the parsed JSON. Mapping to output models happens in `models.py`, not in the client.
- No client-side cache, no retry, no throttling.

### Error mapping

| Qobuz response | Exception |
|---|---|
| 401 | `AuthenticationError` |
| 400 whose message mentions the app id | `InvalidAppIdError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 429, 5xx, network error, timeout | `QobuzUnavailableError` |
| Anything else | `QobuzApiError` |

All inherit from `QobuzError`. Tool handlers let these propagate. A single conversion point in `server.py` turns them into FastMCP `ToolError` with the user-facing messages from FS-BEH-2. Messages are built from the exception type and the requested IDs only, never from request headers or bodies.

## 8. Endpoint mapping

| Tool or command | Endpoint | To validate |
|---|---|---|
| `login` | `user/login` | captcha (FS Q1) |
| `login --token` | `user/get` | existence |
| `search_catalog` | `catalog/search` | |
| `get_album` | `album/get` | |
| `get_track` | `track/get` | |
| `get_artist` | `artist/get` (`extra=albums`) | |
| `get_similar_artists` | `artist/getSimilarArtists` | yes |
| `get_label` | `label/get` (`extra=albums`) | |
| `get_playlist` | `playlist/get` (`extra=tracks`) | |
| `list_genres` | `genre/list` | |
| `list_featured_albums` | `album/getFeatured` | category values |
| `list_featured_playlists` | `playlist/getFeatured` | category values |
| `list_favorites` | `favorite/getUserFavorites` | |
| `list_my_playlists` | `playlist/getUserPlaylists` | |
| `list_purchases` | `purchase/getUserPurchases` | signature (FS Q2) |
| `add_favorites` | `favorite/create` | |
| `remove_favorites` | `favorite/delete` | |
| `create_playlist` | `playlist/create` | |
| `update_playlist` | `playlist/update` | |
| `add_tracks_to_playlist` | `playlist/addTracks` | |
| `remove_tracks_from_playlist` | `playlist/deleteTracks` | |
| `move_playlist_tracks` | `playlist/updateTracksPosition` | existence (FS Q3) |
| `delete_playlist` | `playlist/delete` | |
| `follow_playlist` | `playlist/subscribe` | |
| `unfollow_playlist` | `playlist/unsubscribe` | |

## 9. MCP server

- Transport: stdio only.
- Each tool is an async function with typed parameters and a pydantic return type. FastMCP derives the input schema, the output schema and structured content from them.
- Annotations follow FS section 5. All tools also set `openWorldHint: true`.
- Pagination follows FS-BEH-1; `offset` defaults to 0. List results use a generic `Page[T]` model: `items`, `total`, `limit`, `offset`.
- Public URLs are built in `models.py`: `https://open.qobuz.com/{album|artist|track|playlist|label}/{id}`.
- Server instructions (FS-BEH-5): one constant in `server.py`, passed to the FastMCP instance. It is static text: no content returned by Qobuz is ever interpolated into it or into tool descriptions (FS-BEH-4).
- `create_playlist` sends `is_public` and `is_collaborative` explicitly, `false` unless the caller set them (FS 5.3).
- Logging: standard `logging` to stderr only, since stdout carries the MCP protocol. Level `INFO`. The HTTP stack's loggers (`httpx2` and its transport layer, exact names confirmed at implementation) are capped at `WARNING`, so request details never reach the logs.

## 10. Output models

Tool results are pydantic models in `models.py`. They are the contract the assistant sees, through the output schema FastMCP derives from them. Field lists are completed from the response structures observed during the proof of concept (implementation plan, "Output models" step).

| Model | Used by | Fields |
|---|---|---|
| `Page[T]` | every list tool | `items`, `total`, `limit`, `offset` |
| `AlbumSummary` | search, lists | to be defined |
| `AlbumDetail` | `get_album` | to be defined |
| `TrackSummary` | search, album tracklist | to be defined |
| `TrackDetail` | `get_track` | to be defined |
| `ArtistSummary` | search, lists, similar artists | to be defined |
| `ArtistDetail` | `get_artist` | to be defined |
| `LabelDetail` | `get_label` | to be defined |
| `PlaylistSummary` | search, lists | to be defined |
| `PlaylistDetail` | `get_playlist` | to be defined |
| `PlaylistEntry` | `get_playlist` | `playlist_track_id`, `track` (`TrackSummary`) |
| `Genre` | `list_genres` | to be defined |
| `WriteResult` | write tools | to be defined |

Rules:

- Every catalog model carries `id` and `url` (FS-BEH-1).
- Summaries hold what the assistant needs to pick an item. Details add what the tool's description promises (FS section 5).
- Third-party text fields (names, descriptions, biographies, editorial texts) are returned as plain strings, unmodified (FS-BEH-4).

## 11. Development commands

| Command | Purpose |
|---|---|
| `uv sync` | Install dependencies, including the `dev` group |
| `uv add <package>`, `uv add --dev <package>`, `uv remove <package>` | Manage dependencies. `pyproject.toml` dependency lists and `uv.lock` are never edited by hand |
| `uv run qobuz-mcp <command>` | Run the CLI (section 4) |
| `uv run fastmcp dev src/qobuz_mcp/server.py` | Open the MCP Inspector against the server. Requires Node.js. Exact invocation confirmed at implementation |
| `uv run pytest` | All tests, live tests included |
| `uv run pytest -m "not live"` | Tests without network |
| `uv run ruff check .` and `uv run ruff format --check .` | Lint and format check |
| `uv run mypy` | Type check |
| `uv run coverage run -m pytest -m "not live"` then `uv run coverage report` | Coverage, with the threshold of section 3 |
| `uv run python scripts/check_traceability.py` | Acceptance criteria traceability (section 13) |

## 12. Client configuration

Claude Code:

```sh
claude mcp add qobuz -- uv run --directory /path/to/qobuz-mcp qobuz-mcp serve
```

Claude Desktop (`claude_desktop_config.json`). The absolute path to `uv` is required because Claude Desktop does not inherit the shell `PATH`:

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

## 13. Tests

| Suite | Location | Scope | Runs by default |
|---|---|---|---|
| Unit | `tests/unit/` | `QobuzClient` against `httpx2.MockTransport`, error mapping, model mapping, CLI, `app_id` extraction on fixture HTML and bundle | yes |
| Tools | `tests/unit/` | Each tool through the FastMCP in-memory client with a mocked `QobuzClient` | yes |
| Live | `tests/live/`, marker `live` | The `[live]` acceptance criteria, against the real API | yes |

- Traceability: each test cites in its docstring the acceptance criterion IDs it covers (FS section 7). Every `[test]` and `[live]` criterion delivered by a completed plan step is covered by at least one test.
- `scripts/check_traceability.py` (standard library only) enforces traceability. It reads the criterion IDs and tags from `functional-specifications.md`, the steps of `implementation-plan.md` with their checkbox and `Delivers` list, and the IDs cited in `tests/`. It fails when:
  - a criterion is delivered by no step, or by more than one;
  - a step delivers an unknown ID;
  - a `[test]` or `[live]` criterion of a checked step is not cited by any test;
  - a test cites an unknown ID.
- Unit tests use an in-memory `keyring` backend (`tests/memory_keyring.py`), selected through the `PYTHON_KEYRING_BACKEND` environment variable set in `tests/conftest.py`. Subprocesses started by tests, such as the stdio server of AC-BEH-12, inherit it, so no unit test ever touches the real Keychain.
- Live tests select the macOS Keychain backend explicitly in `tests/live/conftest.py`. If no credentials are found, they are skipped with the reason "not logged in: run `qobuz-mcp login`".
- Live tests never call write endpoints. A request hook on the live `httpx2` client allows only the endpoints of `read-only` tools (FS section 5) and of `app_id` extraction, and fails the test otherwise (AC-LIVE-05).
- `pytest -m "not live"` excludes them.
- Fixtures are synthetic: hand-written minimal JSON reproducing the structure of real responses observed during the proof of concept, with fake IDs, names and texts. The web player HTML and bundle fixtures are small invented snippets containing only the patterns searched for and a fake `app_id`. No real API response, Qobuz file or account data is ever committed (ADR-0023).

## 14. Continuous integration

GitHub Actions. Live tests never run in CI: they need the real account's token, which stays in the local Keychain (FS-BEH-3).

### `ci.yml`

Triggers: push to `main`, pull requests, manual dispatch. Workflow permissions: `contents: read`. A concurrency group cancels superseded runs of the same branch.

| Job | Runner | Steps |
|---|---|---|
| `lint` | `ubuntu-latest` | `uv lock --check`, `uv run ruff check .`, `uv run ruff format --check .` |
| `types` | `ubuntu-latest` | `uv run mypy` |
| `test` | `macos-latest` | `uv sync --locked`, then `uv run coverage run -m pytest -m "not live"` and `uv run coverage report`. Matrix: Python 3.14 (required) and 3.15 (`continue-on-error`, early warning only) |
| `traceability` | `ubuntu-latest` | `uv run python scripts/check_traceability.py`: only criteria of checked plan steps must be cited, so the job passes before features exist |
| `build` | `ubuntu-latest` | `uv build` |
| `links` | `ubuntu-latest` | lychee in offline mode on all Markdown files: internal links and anchors only |
| `secrets` | `ubuntu-latest` | gitleaks on the full history (`fetch-depth: 0`) |
| `workflows` | `ubuntu-latest` | zizmor on `.github/workflows/` |

All jobs set up uv with the official `astral-sh/setup-uv` action, with its cache enabled.

### `codeql.yml`

CodeQL analysis for Python on push to `main`, pull requests and a weekly schedule. Permissions: `contents: read`, `security-events: write`.

Code scanning is free only for public repositories, so `codeql.yml` is added at publication (implementation plan, "Publication" step), not with `ci.yml`.

### Supply chain

- Every third-party action is pinned by full commit SHA, with the version in a trailing comment.
- `dependabot.yml` updates the `github-actions` and `uv` ecosystems weekly, with one grouped pull request per ecosystem.

## 15. Publication

The repository becomes public once the project scaffold and CI are in place (ADR-0024). Contribution rules follow ADR-0022.

### Files

| File | Content |
|---|---|
| `README.md` | At publication: one-line description, status ("in development, not usable yet"), disclaimers, license, links to `specs/` and `CONTRIBUTING.md`. Usage sections are added when the server is usable |
| `CONTRIBUTING.md` | Contributions start with an issue. A pull request is accepted only when linked to an issue the maintainer has approved. Workflow: specification, ADR and acceptance criteria first, then code, following `CLAUDE.md`. Local checks to run before opening a pull request. Conventional Commits |
| `SECURITY.md` | Report vulnerabilities through GitHub private vulnerability reporting, never in public issues. In scope: credential handling, token or personal data leaks, unsafe writes to the user's account, including writes triggered by instructions injected in third-party content (FS-BEH-4). Out of scope: the Qobuz API itself. Supported version: latest `main`. Best-effort response, no committed delay |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | Issue form: version or commit, macOS version, MCP client, steps, expected and actual result, with a reminder never to paste tokens or account data |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | Issue form: need, proposed behavior, impact on the functional scope |
| `.github/ISSUE_TEMPLATE/config.yml` | Blank issues disabled. Link to private vulnerability reporting |
| `.github/pull_request_template.md` | Checklist: linked approved issue, specifications and ADR updated, acceptance criteria covered by tests, local checks run |

The README disclaimers state that:

* the project is not affiliated with, endorsed or sponsored by Qobuz, and "Qobuz" is a trademark used only to indicate compatibility;
* it relies on Qobuz's unofficial web player API, outside Qobuz's terms of service, and may break at any time;
* it is intended for strictly personal use of one's own account;
* it comes with no guarantee of any kind, and the account owner bears the risks of using it;
* write tools rely on the MCP client asking for confirmation: allowlisting them or using an auto-approve mode removes the main safeguard against instructions injected in third-party content (ADR-0025).

### Repository settings

Applied with `gh` at publication, each after confirmation by the maintainer.

| Area | Setting |
|---|---|
| Visibility | Public |
| Features | Issues on. Wiki, Projects and Discussions off |
| Pull requests | Squash merge only, with the pull request title as commit message. Head branches deleted after merge |
| Ruleset on `main` | No deletion, no force push. Changes through pull requests, with every `ci.yml` job and CodeQL passing, except the Python 3.15 test entry. Repository admins may bypass |
| Security | Secret scanning and push protection on. Private vulnerability reporting on. Dependabot alerts and security updates on |
| Actions | Only the actions used by the workflows allowed. Default `GITHUB_TOKEN` permissions read-only. Workflows from outside collaborators' pull requests need approval |
