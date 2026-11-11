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
        return httpx2.Response(404)

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
