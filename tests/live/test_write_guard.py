import httpx2
import pytest

from qobuz_mcp.api import API_BASE_URL
from tests.live.conftest import BlockedRequestError

pytestmark = [pytest.mark.live, pytest.mark.anyio]


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("POST", API_BASE_URL + "playlist/create"),
        ("POST", API_BASE_URL + "favorite/create"),
        ("GET", API_BASE_URL + "playlist/delete"),
        ("GET", "https://example.com/"),
    ],
)
async def test_live_client_blocks_writes_before_sending(
    live_http: httpx2.AsyncClient, method: str, url: str
) -> None:
    """AC-LIVE-05"""
    with pytest.raises(BlockedRequestError):
        await live_http.request(method, url, data={"name": "must never be sent"})
