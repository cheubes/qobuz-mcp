from collections.abc import AsyncIterator

import httpx2
import pytest

from qobuz_mcp.api import API_BASE_URL, REQUEST_TIMEOUT_SECONDS

# Endpoints of the read-only tools (functional specifications, section 5) and user/get.
READ_ONLY_ENDPOINTS = frozenset(
    {
        "catalog/search",
        "album/get",
        "track/get",
        "artist/get",
        "artist/getSimilarArtists",
        "label/get",
        "playlist/get",
        "genre/list",
        "album/getFeatured",
        "playlist/getFeatured",
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


@pytest.fixture
async def live_http() -> AsyncIterator[httpx2.AsyncClient]:
    async with httpx2.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS, event_hooks={"request": [guard_live_request]}
    ) as http:
        yield http
