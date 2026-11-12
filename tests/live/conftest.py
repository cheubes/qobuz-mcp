from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx2
import keyring
import pytest
from fastmcp import Client
from keyring.backends import macOS

from qobuz_mcp import server
from qobuz_mcp.api import API_BASE_URL, REQUEST_TIMEOUT_SECONDS
from qobuz_mcp.credentials import load_credentials

# Endpoints of the read-only tools (functional specifications, section 5) and user/get.
READ_ONLY_ENDPOINTS = frozenset(
    {
        "catalog/search",
        "album/get",
        "album/suggest",
        "radio/album",
        "radio/artist",
        "radio/track",
        "track/get",
        "artist/page",
        "artist/getReleasesList",
        "artist/playlists",
        "artist/getSimilarArtists",
        "label/page",
        "label/getAlbums",
        "label/getTopArtists",
        "label/getNextReleases",
        "label/getPlaylists",
        "label/getAwardedReleases",
        "playlist/get",
        "genre/list",
        "album/getFeatured",
        "discover/newReleases",
        "discover/qobuzissims",
        "discover/idealDiscography",
        "discover/mostStreamed",
        "discover/pressAward",
        "discover/albumOfTheWeek",
        "discover/playlists",
        "favorite/getUserFavorites",
        "playlist/getUserPlaylists",
        "purchase/getUserPurchases",
        "user/get",
    }
)


class BlockedRequestError(Exception):
    """A live test tried to reach something other than the web player or a read endpoint."""


async def guard_live_request(request: httpx2.Request) -> None:
    url = str(request.url)
    if request.url.host == "play.qobuz.com" and request.method == "GET":
        return
    if url.startswith(API_BASE_URL) and request.method == "GET":
        endpoint = request.url.path.removeprefix("/api.json/0.2/")
        if endpoint in READ_ONLY_ENDPOINTS:
            return
    raise BlockedRequestError(f"live tests must not send {request.method} {request.url.path}")


def guarded_http_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS, event_hooks={"request": [guard_live_request]}
    )


@pytest.fixture
async def live_http() -> AsyncIterator[httpx2.AsyncClient]:
    async with guarded_http_client() as http:
        yield http


@pytest.fixture(autouse=True)
def memory_keyring() -> Iterator[None]:
    """Overrides the in-memory backend of tests/conftest.py: live tests use the real Keychain."""
    previous = keyring.get_keyring()
    keyring.set_keyring(macOS.Keyring())  # type: ignore[no-untyped-call]  # untyped in keyring
    yield
    keyring.set_keyring(previous)


@pytest.fixture
async def live_client(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[Client[Any]]:
    """MCP client on the real server, with the real credentials and the guarded HTTP client."""
    if load_credentials() is None:
        pytest.skip("not logged in: run `qobuz-mcp login`")
    monkeypatch.setattr(server, "http_client", guarded_http_client)
    async with Client(server.mcp) as client:
        yield client
