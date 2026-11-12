"""Test doubles for the Qobuz web player, the Qobuz API and the browser."""

import json
import threading
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx2

FIXTURES = Path(__file__).parent / "fixtures"
LOGIN_PAGE = (FIXTURES / "web_player" / "login.html").read_text()
BUNDLE = (FIXTURES / "web_player" / "bundle.js").read_text()
FAKE_APP_ID = "123456789"
FAKE_PRIVATE_KEY = "fakePrivateKey"
FAKE_CODE = "fake-authorization-code"
FAKE_TOKEN = "fake-user-auth-token"
SEARCH_RESULTS = json.loads((FIXTURES / "api" / "catalog_search.json").read_text())
SEARCH_TYPES = ("albums", "artists", "tracks", "playlists")
ALBUM = json.loads((FIXTURES / "api" / "album_get.json").read_text())
TRACK = json.loads((FIXTURES / "api" / "track_get.json").read_text())
PLAYLIST = json.loads((FIXTURES / "api" / "playlist_get.json").read_text())
ARTIST = json.loads((FIXTURES / "api" / "artist_get.json").read_text())
LABEL = json.loads((FIXTURES / "api" / "label_page.json").read_text())
LABEL_ALBUMS = json.loads((FIXTURES / "api" / "label_albums.json").read_text())
FAVORITES = json.loads((FIXTURES / "api" / "favorites.json").read_text())
DISCOVER_PLAYLISTS = json.loads((FIXTURES / "api" / "discover_playlists.json").read_text())
# Write endpoints answer with the playlist object or with a status (proof of concept).
PLAYLIST_WRITE_ENDPOINTS = frozenset(
    {
        "playlist/create",
        "playlist/update",
        "playlist/addTracks",
        "playlist/deleteTracks",
        "playlist/updateTracksPosition",
    }
)
STATUS_WRITE_ENDPOINTS = frozenset(
    {
        "playlist/delete",
        "favorite/create",
        "favorite/delete",
        "playlist/subscribe",
        "playlist/unsubscribe",
    }
)
WRITTEN_PLAYLIST = {
    "id": 301,
    "name": "Synthetic New Playlist",
    "description": "",
    "owner": {"id": 42, "name": "Test User"},
    "tracks_count": 0,
    "duration": 0,
    "is_public": False,
    "is_collaborative": False,
    "public_at": False,
    "created_at": 1700000000,
    "updated_at": 1700000000,
    "users_count": 0,
}
GENRES: list[dict[str, Any]] = [
    {"id": 112, "name": "Pop/Rock", "path": [112], "slug": "pop-rock", "color": "#000000"},
    {"id": 80, "name": "Jazz", "path": [80], "slug": "jazz", "color": "#000000"},
    {"id": 117, "name": "Rock", "path": [117, 112], "slug": "rock", "color": "#000000"},
    {"id": 118, "name": "Indie Rock", "path": [118, 117, 112], "slug": "indie", "color": "#000"},
]
SIMILAR_ARTISTS = {
    "limit": 2,
    "offset": 0,
    "total": 2,
    "items": [
        {"id": 12, "name": "Synthetic Pianist", "albums_count": 7, "slug": "synthetic-pianist"},
        {"id": 13, "name": "Synthetic Composer", "albums_count": 3},
    ],
}


@dataclass
class FakeQobuz:
    """Routes the requests of an httpx2 client to canned web player and API responses."""

    login_page: str = LOGIN_PAGE
    bundle: str = BUNDLE
    web_player_status: int = 200
    oauth_status: int = 200
    valid_tokens: set[str] = field(default_factory=lambda: {FAKE_TOKEN})
    api_responses: dict[str, httpx2.Response] = field(default_factory=dict)
    track: dict[str, Any] = field(default_factory=lambda: dict(TRACK))
    requests: list[httpx2.Request] = field(default_factory=list)

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        path = request.url.path
        if request.url.host == "play.qobuz.com":
            if self.web_player_status != 200:
                return httpx2.Response(self.web_player_status)
            body = self.login_page if path == "/login" else self.bundle
            return httpx2.Response(200, text=body)
        endpoint = path.removeprefix("/api.json/0.2/")
        if endpoint in self.api_responses:
            return self.api_responses[endpoint]
        if path.endswith("/oauth/callback"):
            params = request.url.params
            valid = (
                params.get("code") == FAKE_CODE and params.get("private_key") == FAKE_PRIVATE_KEY
            )
            if self.oauth_status != 200 or not valid:
                return httpx2.Response(401, json={"status": "error", "code": 401})
            return httpx2.Response(200, json={"token": FAKE_TOKEN, "user_id": 42})
        if path.endswith("/user/get"):
            if request.headers.get("X-User-Auth-Token") not in self.valid_tokens:
                return httpx2.Response(401, json={"status": "error", "code": 401})
            return httpx2.Response(200, json={"id": 42, "display_name": "Test User"})
        if request.headers.get("X-User-Auth-Token") not in self.valid_tokens:
            return httpx2.Response(401, json={"status": "error", "code": 401})
        if endpoint == "catalog/search":
            kind = request.url.params["type"]
            payload = {
                group: SEARCH_RESULTS[group] if group == kind else {"total": 0, "items": []}
                for group in SEARCH_TYPES
            }
            return httpx2.Response(200, json=payload)
        if endpoint == "album/get":
            if request.url.params["album_id"] != ALBUM["id"]:
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json=ALBUM)
        if endpoint == "track/get":
            if request.url.params["track_id"] != str(TRACK["id"]):
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json=self.track)
        if endpoint == "playlist/get":
            if request.url.params["playlist_id"] != str(PLAYLIST["id"]):
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json=PLAYLIST)
        if endpoint == "artist/get":
            if request.url.params["artist_id"] != str(ARTIST["id"]):
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json=ARTIST)
        if endpoint == "artist/getSimilarArtists":
            if request.url.params["artist_id"] != str(ARTIST["id"]):
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json={"artists": SIMILAR_ARTISTS})
        if endpoint in ("label/page", "label/getAlbums"):
            if request.url.params["label_id"] != str(LABEL["id"]):
                return httpx2.Response(404, json={"status": "error", "code": 404})
            return httpx2.Response(200, json=LABEL if endpoint == "label/page" else LABEL_ALBUMS)
        if endpoint.startswith("discover/") and endpoint != "discover/playlists":
            return httpx2.Response(200, json=LABEL_ALBUMS)
        if endpoint == "album/getFeatured":
            return httpx2.Response(200, json={"albums": SEARCH_RESULTS["albums"]})
        if endpoint == "discover/playlists":
            return httpx2.Response(200, json=DISCOVER_PLAYLISTS)
        if endpoint == "favorite/getUserFavorites":
            kind = request.url.params["type"]
            return httpx2.Response(200, json={kind: FAVORITES[kind], "user": {"id": 42}})
        if endpoint == "playlist/getUserPlaylists":
            return httpx2.Response(
                200, json={"playlists": SEARCH_RESULTS["playlists"], "user": {"id": 42}}
            )
        if endpoint == "purchase/getUserPurchases":
            kind = request.url.params["type"]
            return httpx2.Response(200, json={kind: SEARCH_RESULTS[kind], "user": {"id": 42}})
        if endpoint in PLAYLIST_WRITE_ENDPOINTS:
            return httpx2.Response(200, json=WRITTEN_PLAYLIST)
        if endpoint in STATUS_WRITE_ENDPOINTS:
            return httpx2.Response(200, json={"status": "success"})
        if endpoint == "genre/list":
            parent = request.url.params.get("parent_id")
            items = [
                genre for genre in GENRES if genre["path"][1:2] == ([int(parent)] if parent else [])
            ]
            return httpx2.Response(
                200,
                json={"genres": {"limit": 25, "offset": 0, "total": len(items), "items": items}},
            )
        return httpx2.Response(404)

    def form(self, endpoint: str) -> dict[str, str]:
        """Form body of the last request to a write endpoint."""
        request = self.api_requests(endpoint)[-1]
        assert request.method == "POST"
        return dict(urllib.parse.parse_qsl(request.content.decode(), keep_blank_values=True))

    def api_requests(self, endpoint: str) -> list[httpx2.Request]:
        return [r for r in self.requests if r.url.path.endswith("/" + endpoint)]

    def client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=httpx2.MockTransport(self.handle))

    def web_player_requests(self) -> list[httpx2.Request]:
        return [request for request in self.requests if request.url.host == "play.qobuz.com"]


def get_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return error.code


@dataclass
class FakeBrowser:
    """Plays the user signing in: hits the callback the way a browser redirected by Qobuz does."""

    code: str | None = FAKE_CODE
    extra_requests: tuple[str, ...] = ("/favicon.ico",)
    opened_urls: list[str] = field(default_factory=list)
    statuses: dict[str, int] = field(default_factory=dict)

    def open(self, url: str) -> bool:
        self.opened_urls.append(url)
        redirect_url = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)["redirect_url"][0]
        threading.Thread(target=self._visit, args=(redirect_url,), daemon=True).start()
        return True

    def _visit(self, redirect_url: str) -> None:
        origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(redirect_url))
        for path in self.extra_requests:
            self.statuses[path] = get_status(origin + path)
        if self.code is not None:
            callback = f"{redirect_url}?{urllib.parse.urlencode({'code_autorisation': self.code})}"
            self.statuses["callback"] = get_status(callback)


def as_json(raw: str | None) -> dict[str, str] | None:
    return None if raw is None else dict(json.loads(raw))
