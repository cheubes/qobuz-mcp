# Technical specifications

Status: approved. Implements [functional-specifications.md](functional-specifications.md).

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
    web_player.py        # app_id and OAuth private key extraction
    oauth.py             # OAuth browser flow and local callback server
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
    __init__.py
    conftest.py
    fakes.py             # test doubles: web player, Qobuz API, browser
    memory_keyring.py    # in-memory keyring backend
    fixtures/            # synthetic API payloads and web player snippets
    unit/
        __init__.py
    live/
        __init__.py
        conftest.py      # guarded live HTTP client (AC-LIVE-05)
```

## 3. Project configuration

All configuration lives in `pyproject.toml`.

- `[build-system]`: `uv_build`.
- `[project.scripts]`: one console script, `qobuz-mcp = "qobuz_mcp.cli:main"`.
- `[project]` declares `license = "CC0-1.0"`, matching `LICENSE`.
- `[dependency-groups]`: `dev` group (section 1).
- `[tool.uv]`: `required-version`, set at scaffold time to the current uv minor version (`>=0.13,<0.14` as of 0.13.7). `astral-sh/setup-uv` reads it, so CI and local runs use the same uv.
- `[tool.ruff]`: `line-length = 100`. Rule sets: `E`, `W`, `F`, `I` (imports), `N` (PEP 8 naming), `UP` (pyupgrade), `B` (bugbear), `SIM`, `ASYNC`, `RUF`. The target version is derived from `requires-python`.
- `[tool.mypy]`: `strict = true`, `plugins = ["pydantic.mypy"]`, `files` covering `src/`, `tests/` and `scripts/`, `mypy_path = "scripts"`.
- `[tool.coverage]`: `source = ["qobuz_mcp"]`, `branch = true`, `fail_under = 90`.
- `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["scripts"]` (so tests import the traceability script), `addopts = ["--strict-markers"]`, marker `live` declared with its description.

Async tests use the anyio plugin (`@pytest.mark.anyio`), with the `anyio_backend` fixture fixed to `asyncio` in `tests/conftest.py`.

## 4. CLI

| Command | Behavior |
|---|---|
| `qobuz-mcp serve` | Starts the MCP server on stdio |
| `qobuz-mcp login` | Extracts the web player values (section 6), runs the OAuth browser flow (section 6), stores credentials |
| `qobuz-mcp login --token` | Prompts for a token (`getpass`), extracts the `app_id`, validates the token with `user/get` (section 8), stores credentials |
| `qobuz-mcp logout` | Deletes the Keychain entry |

`login` prints the account's display name on success and never echoes the token or the authorization code.

## 5. Credentials

- One Keychain item: service `qobuz-mcp`, account `default`.
- Value: JSON object `{"app_id": str, "user_auth_token": str}`. No in-scope endpoint needs the user ID: the token identifies the user.
- `QOBUZ_APP_ID`, when set, overrides the stored `app_id` at read time.
- The server reads the item at each tool call, with no in-memory cache. `login` and `logout` therefore take effect on the next call without restarting the client (FS-SETUP-2). A cache would keep using the token after `logout`, since logging out does not revoke the token on Qobuz's side.
- A missing item does not prevent the server from starting: tools return the "not logged in" error (FS-BEH-2) until the user logs in.

Known limitation: Keychain access is granted to the Python interpreter binary that created the item. When uv upgrades the interpreter, macOS asks again for Keychain access on the next run.

## 6. Web player values and OAuth login

### Extraction

The CLI reads two values from the web player bundle. The login page needs no specific `User-Agent`.

1. `GET https://play.qobuz.com/login`.
2. Find the bundle path in the HTML: `src="(/resources/[^"]+/bundle\.js)"`.
3. `GET` the bundle (about 10 MB).
4. Extract:
   - `app_id`: `production:\{api:\{appId:"(\d{9})"`, which matches the production configuration only;
   - OAuth private key: `authenticate\(\{privateKey:"([^"]+)"`.

The patterns were confirmed during the proof of concept on bundle `8.3.0-b029` and are covered by live tests (AC-LIVE-01, AC-LIVE-06). An `app_id` extraction failure raises `AppIdExtractionError`, whose message suggests setting `QOBUZ_APP_ID`. A private key extraction failure raises `PrivateKeyExtractionError`, whose message suggests `login --token`. When the page or the bundle cannot be loaded at all, `WebPlayerError` is reported as whichever of these two errors `login` still needs: with `QOBUZ_APP_ID` set, only the private key is missing. `login --token` with `QOBUZ_APP_ID` set does not load the web player at all. The bundle also holds an `appSecret`, which the server does not need: no in-scope endpoint requires a request signature.

### OAuth browser flow

1. Start an HTTP server on `127.0.0.1`, on a free port chosen by the OS, accepting only `GET /callback/<nonce>`, where `<nonce>` is a random value generated for this login. Every other request gets a 404 and is ignored (AC-SETUP-14).
2. Open `https://www.qobuz.com/signin/oauth?ext_app_id=<app_id>&redirect_url=<callback URL>` with `webbrowser`, and print it.
3. Qobuz redirects the browser to `<callback URL>?code_autorisation=<code>`. The server answers with a short page telling the user to close the tab, then stops.
4. `GET oauth/callback?code=<code>&private_key=<private key>` with `X-App-Id`. The response holds `token` and `user_id`, and only `token` is kept.
5. Call `user/get` with the token, which validates it and gives the display name `login` prints.
6. Store the credentials (section 5).

Timeout: 5 minutes, after which the server stops, `LoginTimeoutError` is raised and nothing is stored. The server never logs requests: the default request log line would contain the authorization code. Qobuz accepted a `127.0.0.1` redirect during the proof of concept. The random path segment keeps a stray or forged request from being taken for the callback, since the flow has no `state` parameter.

## 7. Qobuz API client

`QobuzClient` wraps one shared `httpx2.AsyncClient`, created and closed in the FastMCP lifespan.

- Base URL: `https://www.qobuz.com/api.json/0.2/`.
- Headers on every call: `X-App-Id`, and `X-User-Auth-Token` for authenticated calls.
- Timeout: 15 seconds.
- One method per endpoint, returning the parsed JSON. Mapping to output models happens in `models.py`, not in the client.
- No client-side cache, no retry, no throttling.
- Reads are `GET` with query parameters. Writes are `POST` with an `application/x-www-form-urlencoded` body, as the web player does.
- ID lists are sent comma-separated (`track_ids=1,2,3`). Booleans are sent as `true` or `false`.
- Every catalog endpoint requires the token, including `catalog/search`.
- No specific `User-Agent` is required. The HTTP client's default is kept.

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

All endpoints below were called successfully during the proof of concept.

| Tool or command | Endpoint | Parameters and notes |
|---|---|---|
| `login` | `oauth/callback` | `code`, `private_key` (section 6) |
| `login --token` | `user/get` | Token validation: 200 when valid, 401 otherwise |
| `search_catalog` | `catalog/search` | `query`, `type` (`albums`, `artists`, `tracks`, `playlists`), `limit`, `offset`. With `type`, the other result groups come back empty |
| `get_album` | `album/get` | `album_id`. The booklet is in `goodies` |
| `get_track` | `track/get` | `track_id`. Credits come as one string in `performers` |
| `get_artist` | `artist/get` | `artist_id`, `extra=albums`, `limit`, `offset` |
| `get_similar_artists` | `artist/getSimilarArtists` | `artist_id`, `limit`, `offset` |
| `get_label` | `label/get` | `label_id`, `extra=albums`, `limit`, `offset` |
| `get_playlist` | `playlist/get` | `playlist_id`, `extra=tracks`, `limit`, `offset`. Entries carry `playlist_track_id` and `position` |
| `list_genres` | `genre/list` | `parent_id` (optional) |
| `list_featured_albums` | `album/getFeatured` | `type`, `genre_ids` (optional), `limit`, `offset`. Accepted `type` values, as listed by the API: `new-releases`, `new-releases-full`, `recent-releases`, `press-awards`, `best-sellers`, `most-streamed`, `editor-picks`, `most-featured`, `ideal-discography`, `qobuzissims`, `harmonia-mundi`, `universal-classic`, `universal-jazz`, `universal-jeunesse`, `universal-chanson` |
| `list_featured_playlists` | `playlist/getFeatured` | `type=editor-picks` (sent as the web player does, but ignored by the API), `genre_ids` (optional), `limit`, `offset` |
| `list_favorites` | `favorite/getUserFavorites` | `type` (`albums`, `artists`, `tracks`), `limit`, `offset` |
| `list_my_playlists` | `playlist/getUserPlaylists` | `filter` (`owner` or `subscriber`, mapped from `owned` and `followed`; omitted for both), `limit`, `offset` |
| `list_purchases` | `purchase/getUserPurchases` | `type` (`albums`, `tracks`), `limit`, `offset`. No signature needed |
| `add_favorites` | `favorite/create` | `album_ids`, `artist_ids`, `track_ids` |
| `remove_favorites` | `favorite/delete` | `album_ids`, `artist_ids`, `track_ids` |
| `create_playlist` | `playlist/create` | `name`, `description`, `is_public`, `is_collaborative` |
| `update_playlist` | `playlist/update` | `playlist_id` and the fields to change only. Omitted fields are kept |
| `add_tracks_to_playlist` | `playlist/addTracks` | `playlist_id`, `track_ids`, `no_duplicate` |
| `remove_tracks_from_playlist` | `playlist/deleteTracks` | `playlist_id`, `playlist_track_ids` |
| `move_playlist_tracks` | `playlist/updateTracksPosition` | `playlist_id`, `playlist_track_ids`, `insert_before`: the entries are moved before the entry currently at that 1-based position, `0` meaning first. Moving to the end (`tracks_count + 1`) is inferred, not observed |
| `delete_playlist` | `playlist/delete` | `playlist_id` |
| `follow_playlist` | `playlist/subscribe` | `playlist_id` |
| `unfollow_playlist` | `playlist/unsubscribe` | `playlist_id` |

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

Tool results are pydantic models in `models.py`. They are the contract the assistant sees, through the output schema FastMCP derives from them. Fields come from the response structures observed during the proof of concept. Each model keeps only what the assistant needs, never the raw payload (FS-BEH-1).

### Conventions

- IDs keep Qobuz's types: album IDs are strings, all other IDs are integers.
- Every catalog model carries `id` and `url`, the public `https://open.qobuz.com/<kind>/<id>` URL (FS-BEH-1).
- Dates are ISO 8601 strings: `YYYY-MM-DD` for release dates, UTC date-times for Qobuz timestamps.
- Durations are in seconds, in fields named `duration_seconds`.
- Optional fields are `None` when Qobuz omits them or sends `null`.
- Third-party text fields (names, descriptions, biographies, editorial texts, credits) are returned as plain strings, unmodified (FS-BEH-4).
- No image URLs: the assistant cannot use them, and they cost context.

### Shared models

| Model | Fields | Source |
|---|---|---|
| `Page[T]` | `items: list[T]`, `total`, `limit`, `offset` | Qobuz page objects. The `artists` group of `catalog/search` has no `limit` or `offset`, which are then filled from the request |
| `ArtistRef` | `id`, `name` | `artist`, `performer`, `composer` objects |
| `ArtistCredit` | `id`, `name`, `roles: list[str]` | `album/get` `artists[]` |
| `LabelRef` | `id`, `name` | `label` objects |
| `GenreRef` | `id`, `name` | `genre` and `genres[]` objects |
| `AlbumRef` | `id`, `title` | `album` object inside a track |
| `OwnerRef` | `id`, `name` | playlist `owner` |
| `AudioQuality` | `bit_depth`, `sampling_rate_khz: float`, `channels`, `hires: bool` | `maximum_bit_depth`, `maximum_sampling_rate`, `maximum_channel_count`, `hires` |
| `Favorite[T]` | `item: T`, `favorited_at` | `favorite/getUserFavorites` items, whose `favorited_at` timestamp is present for albums, artists and tracks |

### Catalog models

| Model | Used by | Fields |
|---|---|---|
| `AlbumSummary` | search, artist and label discographies, featured albums, favorites, purchases | `id: str`, `url`, `title`, `version`, `artist: ArtistRef`, `release_date`, `tracks_count`, `duration_seconds`, `genre: GenreRef`, `label: LabelRef`, `audio_quality: AudioQuality`, `parental_warning`, `streamable` |
| `AlbumDetail` | `get_album` | `AlbumSummary` fields, plus `artists: list[ArtistCredit]`, `composer: ArtistRef`, `release_type`, `description`, `awards: list[Award]`, `booklets: list[Booklet]`, `copyright`, `upc`, `tracks: Page[TrackSummary]` |
| `Award` | `AlbumDetail` | `name`, `publication_name`, `awarded_at` |
| `Booklet` | `AlbumDetail` | `name`, `url` (from `goodies[]`) |
| `TrackSummary` | search, album tracklist, playlist entries, favorites, purchases | `id: int`, `url`, `title`, `version`, `performer: ArtistRef`, `album: AlbumRef`, `track_number`, `media_number`, `duration_seconds`, `audio_quality: AudioQuality`, `parental_warning`, `streamable` |
| `TrackDetail` | `get_track` | `TrackSummary` fields, plus `composer: ArtistRef`, `work`, `credits` (the raw `performers` string, not parsed: its format is not documented), `isrc`, `copyright`, `release_date` |
| `ArtistSummary` | search, similar artists, favorites | `id: int`, `url`, `name`, `albums_count` |
| `ArtistDetail` | `get_artist` | `ArtistSummary` fields, plus `biography` (from `biography.content`), `albums: Page[AlbumSummary]` |
| `LabelDetail` | `get_label` | `id: int`, `url`, `name`, `description`, `albums: Page[AlbumSummary]` |
| `PlaylistSummary` | search, featured playlists, user playlists, playlist writes | `id: int`, `url`, `name`, `description`, `owner: OwnerRef`, `tracks_count`, `duration_seconds`, `is_public`, `is_collaborative`, `updated_at` |
| `PlaylistDetail` | `get_playlist` | `PlaylistSummary` fields, plus `genres: list[GenreRef]`, `entries: Page[PlaylistEntry]` |
| `PlaylistEntry` | `PlaylistDetail` | `playlist_track_id`, `position`, `track: TrackSummary` |
| `Genre` | `list_genres` | `id`, `name`, `path: list[int]` (IDs of the parent genres) |

### Tool results

| Tool | Result |
|---|---|
| `search_catalog` | `Page` of the model matching `type`: `AlbumSummary`, `ArtistSummary`, `TrackSummary` or `PlaylistSummary` |
| `get_album`, `get_track`, `get_artist`, `get_label`, `get_playlist` | The matching detail model |
| `get_similar_artists` | `Page[ArtistSummary]` |
| `list_genres` | `Page[Genre]` |
| `list_featured_albums` | `Page[AlbumSummary]` |
| `list_featured_playlists`, `list_my_playlists` | `Page[PlaylistSummary]` |
| `list_favorites` | `Page` of `Favorite[AlbumSummary]`, `Favorite[ArtistSummary]` or `Favorite[TrackSummary]`, matching `type`, newest first, as Qobuz returns them |
| `list_purchases` | `Page` of `AlbumSummary` or `TrackSummary`, matching `type`. Assumed to share the album and track structures: the test account had no purchase to observe |
| `create_playlist`, `update_playlist`, `add_tracks_to_playlist`, `remove_tracks_from_playlist`, `move_playlist_tracks` | `PlaylistSummary`, the playlist's state after the write, as returned by Qobuz |
| `delete_playlist`, `add_favorites`, `remove_favorites`, `follow_playlist`, `unfollow_playlist` | `WriteResult`: `status`, the value Qobuz returns (`success` when the write succeeded) |

`AlbumDetail.tracks` is the page of tracks Qobuz returns with the album. Its `total` tells whether the tracklist is complete. Only one album was observed, so the page size for long albums (box sets) is checked when `get_album` is implemented.

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
- `scripts/check_traceability.py` (standard library only) enforces traceability. It reads the criterion IDs and tags from `functional-specifications.md`, and the steps of `implementation-plan.md` with their checkbox and `Delivers` list. It collects the IDs cited in the docstrings of `tests/` (module, class and function docstrings only, so IDs used as test data are not citations). It fails when:
  - a criterion is delivered by no step, or by more than one;
  - a step delivers an unknown ID;
  - a `[test]` or `[live]` criterion of a checked step is not cited by any test;
  - a test cites an unknown ID;
  - a `[retired]` criterion is delivered by a step or cited by a test.
  `[retired]` criteria are otherwise ignored.
- Unit tests use an in-memory `keyring` backend (`tests/memory_keyring.py`), selected through the `PYTHON_KEYRING_BACKEND` environment variable set in `tests/conftest.py`. Subprocesses started by tests, such as the stdio server of AC-BEH-12, inherit it, so no unit test ever touches the real Keychain.
- Live tests select the macOS Keychain backend explicitly in `tests/live/conftest.py`. If no credentials are found, they are skipped with the reason "not logged in: run `qobuz-mcp login`".
- Live tests never call write endpoints. A request hook on the live `httpx2` client allows only the endpoints of `read-only` tools (FS section 5), `user/get` and the web player pages, and fails the test otherwise (AC-LIVE-05).
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
| `workflows` | `ubuntu-latest` | zizmor, offline, on `.github/` (workflows and Dependabot configuration), run with `uvx` at a pinned version |

All jobs set up uv with the official `astral-sh/setup-uv` action, with its cache enabled.

### `codeql.yml`

CodeQL analysis for Python on push to `main`, pull requests and a weekly schedule. Permissions: `contents: read`, `security-events: write`.

Code scanning is free only for public repositories, so `codeql.yml` is added at publication (implementation plan, "Publication" step), not with `ci.yml`.

### Supply chain

- Every third-party action is pinned by full commit SHA, with the version in a trailing comment.
- `dependabot.yml` updates the `github-actions` and `uv` ecosystems weekly, with one grouped pull request per ecosystem, and a 7-day cooldown so that brand-new releases are not adopted immediately.
- `actions/checkout` runs with `persist-credentials: false`, so later steps cannot reuse the token.

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
