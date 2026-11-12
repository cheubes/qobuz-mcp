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
        common.py        # client built from fresh credentials, pagination parameters
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
- Generic `get`, `post` and `post_json` methods handle parameter encoding, headers and error mapping. One method per endpoint builds on them, returning the parsed JSON. Each endpoint method is added with the tool that uses it (implementation plan, steps 8 to 14). Mapping to output models happens in `models.py`, not in the client.
- No client-side cache, no retry, no throttling.
- Reads are `GET` with query parameters. Writes are `POST` with an `application/x-www-form-urlencoded` body, as the web player does. One read, `dynamic/suggest`, is a `POST` with a JSON body, as the web player sends it (ADR-0031).
- ID lists are sent comma-separated (`track_ids=1,2,3`). Booleans are sent as `true` or `false`.
- Every catalog endpoint requires the token, including `catalog/search`.
- No specific `User-Agent` is required. The HTTP client's default is kept.

### Error mapping

| Qobuz response | Exception |
|---|---|
| 401 | `AuthenticationError` |
| 400 whose message mentions the app id (Qobuz: "Invalid or missing app_id parameter") | `InvalidAppIdError` |
| 403 | `ForbiddenError` |
| 404 | `NotFoundError` |
| 429, 5xx, network error, timeout | `QobuzUnavailableError` |
| Anything else, including a 200 whose body is not a JSON object | `QobuzApiError` |

All inherit from `QobuzError`. Tool handlers let these propagate. A single conversion point in `server.py` turns them into FastMCP `ToolError` with the user-facing messages from FS-BEH-2. Messages are built from the exception type and the requested IDs only, never from request headers or bodies.

## 8. Endpoint mapping

All endpoints below were called successfully during the proof of concept, or during the read-only probes of the catalog extension (ADR-0031). Endpoints marked "has_more" paginate with `has_more` and give no total (ADR-0032). The "current format" is the album, track and playlist structure of the current web player endpoints (section 10).

| Tool or command | Endpoint | Parameters and notes |
|---|---|---|
| `login` | `oauth/callback` | `code`, `private_key` (section 6) |
| `login --token` | `user/get` | Token validation: 200 when valid, 401 otherwise |
| `search_catalog` | `catalog/search` | `query`, `type` (`albums`, `artists`, `tracks`, `playlists`), `limit`, `offset`. With `type`, the other result groups come back empty |
| `get_album` | `album/get` | `album_id`, `limit`, `offset` (for the tracklist; Qobuz returns up to 500 tracks without them). The booklet is in `goodies` |
| `get_track` | `track/get` | `track_id`. Credits come as one string in `performers` |
| `get_artist` | `artist/page`, then `artist/getReleasesList` | `artist/page`: `artist_id`, `sort=relevant`. It gives the name (`name.display`) and the biography (`biography.content`, simple HTML). `artist/getReleasesList`: `artist_id`, `release_type` (optional), `sort=release_date`, `limit`, `offset`, has_more, current format. `release_type` values: `album` observed; `live`, `compilation`, `epSingle` and `other`, the release groups of `artist/page`, assumed. The result without `release_type` is confirmed at implementation (ADR-0036) |
| `get_similar_artists` | `artist/getSimilarArtists` | `artist_id`, `limit`, `offset` |
| `get_label` | `label/page`, then `label/getAlbums` | `label/page`: `label_id`. It gives the name and description. `label/getAlbums`: `label_id`, `limit`, `offset`, has_more, current format (ADR-0034) |
| `get_playlist` | `playlist/get` | `playlist_id`, `extra=tracks`, `limit`, `offset`. Entries carry `playlist_track_id` and `position` |
| `list_genres` | `genre/list` | `parent_id` (optional), `limit`, `offset`. Qobuz's `path` lists the genre itself, then its ancestors up to the root |
| `list_featured_albums` | `discover/*` or `album/getFeatured`, by category (ADR-0035) | Categories `new-releases`, `qobuzissims`, `ideal-discography`, `most-streamed`, `press-awards` and `album-of-the-week` go to `discover/newReleases`, `discover/qobuzissims`, `discover/idealDiscography`, `discover/mostStreamed`, `discover/pressAward` and `discover/albumOfTheWeek`: `genre_ids` (optional), `limit`, `offset`, has_more, current format. `genre_ids` observed on `discover/newReleases`, assumed on the others. The other categories go to `album/getFeatured`: `type`, `genre_ids` (optional), `limit`, `offset`. Its other accepted `type` values, as listed by the API: `new-releases-full`, `recent-releases`, `best-sellers`, `editor-picks`, `most-featured`, `harmonia-mundi`, `universal-classic`, `universal-jazz`, `universal-jeunesse`, `universal-chanson` |
| `list_featured_playlists` | `discover/playlists` | `genre_ids` (optional), `tags` (optional: one of the slugs listed in ADR-0033), `limit`, `offset`, has_more, current format |
| `list_similar_albums` | `album/suggest` | `album_id`. Returns 30 albums in `albums.items`, current format |
| `get_radio` | `radio/album`, `radio/artist` or `radio/track`, by `seed_type` | `album_id`, `artist_id` or `track_id`. Returns 30 tracks in `tracks.items`, current format |
| `suggest_tracks` | `track/get` for each given track, then `dynamic/suggest` | `track/get` gives each track's `performer.id`, `album.label.id` and `album.genre.id`. `dynamic/suggest` is a `POST` with the JSON body `{"limit", "listened_tracks_ids", "track_to_analysed"}`: `listened_tracks_ids` holds the given track IDs, which are then not suggested, and `track_to_analysed` holds one `{"track_id", "artist_id", "label_id", "genre_id"}` object per given track, with `0` for a missing ID, as the web player does. Returns `tracks.items` in the `track/get` format |
| `list_artist_playlists` | `artist/playlists` | `artist_id`, `limit`, `offset`, has_more, current format |
| `list_label_items` | `label/getTopArtists`, `label/getNextReleases`, `label/getPlaylists` or `label/getAwardedReleases`, by `section` (`top_artists`, `upcoming_releases`, `playlists`, `awarded_releases`) | `label_id`, `limit`, `offset`, has_more, current format. Top artists carry only `id`, `name` and an image |
| `list_awards` | `award/explore` | `limit`, `offset`, has_more. Items carry `id`, `name` and `magazine.name` |
| `get_award` | `award/page`, then `award/getAlbums` | `award/page`: `award_id`. It gives the name. `award/getAlbums`: `award_id`, `genre_ids` (optional), `limit`, `offset`, has_more, current format |
| `search_stories` | `story/search` | `query`, `limit`, `offset`. The page is under `stories`, with a `total` |
| `list_related_stories` | `album/story`, `artist/story`, `label/story`, `playlist/story` or `award/story`, by `entity_type` | `album_id`, `artist_id`, `label_id`, `playlist_id` or `award_id`, `limit`, `offset`, has_more. `playlist/story` is assumed to match the others: not observed |
| `list_favorites` | `favorite/getUserFavorites` | `type` (`albums`, `artists`, `tracks`), `limit`, `offset` |
| `list_my_playlists` | `playlist/getUserPlaylists` | `filter` (`owner` or `subscriber`, mapped from `owned` and `followed`; omitted for both), `limit`, `offset` |
| `list_purchases` | `purchase/getUserPurchases` | `type` (`albums`, `tracks`), `limit`, `offset`. No signature needed |
| `list_new_releases_from_favorites` | `favorite/getNewReleases` | `type` (`artists`, `labels`, `awards`, from `source`), `genre_ids` (optional), `limit`, `offset`, has_more, current format |
| `check_library` | `favorite/getUserFavoriteIds`, then `purchase/getUserPurchasesIds` | No parameter. Favorites come as ID lists under `albums` (strings), `artists` and `tracks` (integers), all in one response: thousands of IDs observed. Purchases come under `albums.items` and `tracks.items`, each with a `total`, alongside a `user` object holding the account login, which is dropped (FS-BEH-3). The purchase item structure is not observed, since the account has no purchase: items are accepted as IDs or as objects with an `id`. Whether purchases are paginated is not observed either |
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

- Transport: stdio only. `serve` starts it without FastMCP's banner.
- One `httpx2.AsyncClient`, created by the FastMCP lifespan, is shared by all tool calls. FastMCP runs one lifespan while any session is open.
- Tools build a `QobuzClient` from credentials read at each call (`tools/common.py`, section 5).
- Error conversion: FastMCP wraps every exception raised in a tool into a `ToolError`, keeping the original in `__cause__`. A middleware in `server.py` replaces it with a `ToolError` carrying the `QobuzError` message. `mask_error_details=True` hides the details of any other exception, so an unexpected error never leaks internal data.
- A result typed as a union of models, such as `search_catalog`'s, is wrapped by FastMCP in a `result` object.
- Each tool is an async function with typed parameters and a pydantic return type. FastMCP derives the input schema, the output schema and structured content from them.
- Annotations follow FS section 5. All tools also set `openWorldHint: true`.
- Pagination follows FS-BEH-1; `offset` defaults to 0. List results use a generic `Page[T]` model: `items`, `has_more`, `total`, `limit`, `offset` (ADR-0032).
- Public URLs are built in `models.py`: `https://open.qobuz.com/{album|artist|track|playlist|label}/{id}`, and `https://play.qobuz.com/{award|story}/{id}`, the web player routes `award/:awardId` and `story/:id`, for awards and stories.
- Server instructions (FS-BEH-5): one constant in `server.py`, passed to the FastMCP instance. It is static text: no content returned by Qobuz is ever interpolated into it or into tool descriptions (FS-BEH-4).
- `create_playlist` sends `is_public` and `is_collaborative` explicitly, `false` unless the caller set them (FS 5.3).
- Logging: standard `logging` to stderr only, since stdout carries the MCP protocol. Level `INFO`. The HTTP stack's loggers (`httpx2` and its transport layer, exact names confirmed at implementation) are capped at `WARNING`, so request details never reach the logs.

## 10. Output models

Tool results are pydantic models in `models.py`. They are the contract the assistant sees, through the output schema FastMCP derives from them. Fields come from the response structures observed during the proof of concept. Each model keeps only what the assistant needs, never the raw payload (FS-BEH-1).

### Conventions

- IDs keep Qobuz's types: album IDs are strings, all other IDs are integers.
- Every catalog model carries `id` and `url`, its public URL (FS-BEH-1, section 9).
- Dates are ISO 8601 strings: `YYYY-MM-DD` for release dates, UTC date-times for Qobuz timestamps.
- Durations are in seconds, in fields named `duration_seconds`.
- Optional fields are `None` when Qobuz omits them or sends `null`.
- Third-party text fields (names, descriptions, biographies, editorial texts, credits) are returned as plain strings, unmodified (FS-BEH-4). The only exception is the default artist biography, an exact prefix of Qobuz's text (ADR-0036).
- No image URLs: the assistant cannot use them, and they cost context.

### Shared models

| Model | Fields | Source |
|---|---|---|
| `Page[T]` | `items: list[T]`, `has_more: bool`, `total: int \| None`, `limit`, `offset` | Qobuz page objects. The `artists` group of `catalog/search` has no `limit` or `offset`, which are then filled from the request, as for every page that omits them. `has_more` is Qobuz's when sent, `offset + len(items) < total` otherwise. `total` is `None` when Qobuz gives none. A fixed list, such as a radio, is one complete page: `total` is its length, `has_more` is `false`, `offset` is 0 and `limit` is its length (ADR-0032) |
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
| `AlbumSummary` | search, artist and label discographies, featured and similar albums, award albums, label sections, new releases from favorites, favorites, purchases | `id: str`, `url`, `title`, `version`, `artist: ArtistRef`, `release_date`, `tracks_count`, `duration_seconds`, `genre: GenreRef`, `label: LabelRef`, `audio_quality: AudioQuality`, `parental_warning`, `streamable` |
| `AlbumDetail` | `get_album` | `AlbumSummary` fields, plus `artists: list[ArtistCredit]`, `composer: ArtistRef`, `release_type`, `description`, `awards: list[Award]`, `booklets: list[Booklet]`, `copyright`, `upc`, `tracks: Page[TrackSummary]` |
| `Award` | `AlbumDetail` | `name`, `publication_name`, `awarded_at` |
| `Booklet` | `AlbumDetail` | `name`, `url` (from `goodies[]`) |
| `TrackSummary` | search, album tracklist, playlist entries, radios, track suggestions, favorites, purchases | `id: int`, `url`, `title`, `version`, `performer: ArtistRef`, `album: AlbumRef`, `track_number`, `media_number`, `duration_seconds`, `audio_quality: AudioQuality`, `parental_warning`, `streamable` |
| `TrackDetail` | `get_track` | `TrackSummary` fields, plus `composer: ArtistRef`, `work`, `credits` (the raw `performers` string, not parsed: its format is not documented), `isrc`, `copyright`, `release_date` |
| `ArtistSummary` | search, similar artists, label top artists, favorites | `id: int`, `url`, `name`, `albums_count` |
| `ArtistDetail` | `get_artist` | `ArtistSummary` fields, `albums_count` being `None` since `artist/page` does not provide it, plus `biography`, `biography_truncated: bool`, `albums: Page[AlbumSummary]`. `biography` comes from `biography.content`, simple HTML of up to about 12,000 characters observed. By default, it is the longest prefix of at most 1,000 characters that ends right after a `.`, `!` or `?`, or at the last whitespace when none fits, and `biography_truncated` is `true` when text was cut. With `full_biography`, it is the full text and `biography_truncated` is `false`. `None` and `false` when Qobuz has no biography (ADR-0036) |
| `LabelDetail` | `get_label` | `id: int`, `url`, `name`, `description`, `albums: Page[AlbumSummary]` |
| `AwardSummary` | `list_awards` | `id: int`, `url`, `name`, `publication_name` (from `magazine.name`) |
| `AwardDetail` | `get_award` | `id: int`, `url`, `name`, `albums: Page[AlbumSummary]` |
| `StorySummary` | `search_stories`, `list_related_stories` | `id: str`, `url`, `title`, `summary` (from `description_short`), `authors: list[str]` (author names), `published_at` (from `display_date`, Unix seconds), `sections: list[str]` (from `section_slugs`, such as `/news`) |
| `ItemStatus` | `check_library` | `id` (string for albums, integer otherwise), `favorite: bool`, `purchased: bool \| None` (`None` for artists, which cannot be purchased) |
| `LibraryStatus` | `check_library` | `albums`, `artists`, `tracks`: each a `list[ItemStatus]`, in the order of the given IDs |
| `PlaylistSummary` | search, featured, artist and label playlists, user playlists, playlist writes | `id: int`, `url`, `name`, `description`, `owner: OwnerRef`, `tracks_count`, `duration_seconds`, `is_public`, `is_collaborative`, `updated_at` |
| `PlaylistDetail` | `get_playlist` | `PlaylistSummary` fields, plus `genres: list[GenreRef]`, `entries: Page[PlaylistEntry]` |
| `PlaylistEntry` | `PlaylistDetail` | `playlist_track_id`, `position`, `track: TrackSummary` |
| `Genre` | `list_genres` | `id`, `name`, `path: list[int]` (IDs of the ancestor genres, from the root to the direct parent, empty for a top-level genre) |

### Tool results

| Tool | Result |
|---|---|
| `search_catalog` | `Page` of the model matching `type`: `AlbumSummary`, `ArtistSummary`, `TrackSummary` or `PlaylistSummary` |
| `list_similar_albums`, `list_new_releases_from_favorites` | `Page[AlbumSummary]` |
| `get_radio`, `suggest_tracks` | `Page[TrackSummary]`. `suggest_tracks` returns one complete page of up to `limit` tracks |
| `list_artist_playlists` | `Page[PlaylistSummary]` |
| `list_label_items` | `Page` of the model matching `section`: `ArtistSummary` for `top_artists`, `PlaylistSummary` for `playlists`, `AlbumSummary` otherwise |
| `list_awards` | `Page[AwardSummary]` |
| `get_award` | `AwardDetail` |
| `search_stories`, `list_related_stories` | `Page[StorySummary]` |
| `check_library` | `LibraryStatus` |
| `get_album`, `get_track`, `get_artist`, `get_label`, `get_playlist` | The matching detail model |
| `get_similar_artists` | `Page[ArtistSummary]` |
| `list_genres` | `Page[Genre]` |
| `list_featured_albums` | `Page[AlbumSummary]` |
| `list_featured_playlists`, `list_my_playlists` | `Page[PlaylistSummary]` |
| `list_favorites` | `Page` of `Favorite[AlbumSummary]`, `Favorite[ArtistSummary]` or `Favorite[TrackSummary]`, matching `type`, newest first, as Qobuz returns them |
| `list_purchases` | `Page` of `AlbumSummary` or `TrackSummary`, matching `type`. Assumed to share the album and track structures: the test account had no purchase to observe |
| `create_playlist`, `update_playlist`, `add_tracks_to_playlist`, `remove_tracks_from_playlist`, `move_playlist_tracks` | `PlaylistSummary`, the playlist's state after the write, as returned by Qobuz |
| `delete_playlist`, `add_favorites`, `remove_favorites`, `follow_playlist`, `unfollow_playlist` | `WriteResult`: `status`, the value Qobuz returns (`success` when the write succeeded) |

`AlbumDetail.tracks` is one page of the tracklist, paginated like any list (FS-BEH-1). Its `has_more` tells whether more tracks exist. Tracks inside an album carry no `album` object in Qobuz's answer, so `album` is filled from the album itself.

### Current web player formats

The current web player endpoints return albums, tracks and playlists in another structure than the endpoints of the proof of concept. They map to the same models:

| Model | Source fields |
|---|---|
| `AlbumSummary` | `artist` from `artist` when present, its name in `name.display`, otherwise the first of `artists[]`. `release_date` from `dates.original`. `tracks_count` from `track_count` or `tracks_count`. `audio_quality` from `audio_info`, with `hires` from `rights.hires_streamable`. `streamable` from `rights.streamable` |
| `TrackSummary` | `performer` from the first of `artists[]`. `track_number` and `media_number` from `physical_support`. `audio_quality` and `streamable` as for albums. `album` from `album` |
| `PlaylistSummary` | `name` from `name`, or `title` for `artist/playlists`. `is_public` and `is_collaborative` are `None`: editorial playlists do not carry them |
| `ArtistSummary` | `name` from `name`, or `name.display`. `albums_count` is `None` |

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
- Live tests never call write endpoints. A request hook on the live `httpx2` client allows only `GET` requests to the endpoints of `read-only` tools (FS section 5), `user/get` and the web player pages, and fails the test otherwise (AC-LIVE-05). `dynamic/suggest` is a `POST`, so the hook blocks it: `suggest_tracks` has no live test (ADR-0031).
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
