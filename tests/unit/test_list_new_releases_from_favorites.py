from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

pytestmark = pytest.mark.anyio


@pytest.fixture
def fake_qobuz(monkeypatch: pytest.MonkeyPatch) -> FakeQobuz:
    fake = FakeQobuz()
    monkeypatch.setattr(server, "http_client", fake.client)
    return fake


@pytest.fixture
async def client(fake_qobuz: FakeQobuz) -> AsyncIterator[Client[Any]]:
    save_credentials(Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN))
    async with Client(server.mcp) as connected:
        yield connected


@pytest.mark.parametrize("source", ["artists", "labels", "awards"])
async def test_releases_of_the_requested_favorite_type(
    client: Client[Any], fake_qobuz: FakeQobuz, source: str
) -> None:
    """AC-LIB-09"""
    result = await client.call_tool(
        "list_new_releases_from_favorites", {"source": source, "genre_id": 80, "limit": 5}
    )
    page = result.structured_content
    assert page is not None
    assert page["items"][0]["url"] == "https://open.qobuz.com/album/0000000000021"
    assert (page["has_more"], page["total"]) == (True, None)
    request = fake_qobuz.api_requests("favorite/getNewReleases")[-1]
    assert dict(request.url.params) == {
        "type": source,
        "genre_ids": "80",
        "limit": "5",
        "offset": "0",
    }


async def test_unknown_source_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_new_releases_from_favorites", {"source": "albums"}, raise_on_error=False
    )
    assert result.is_error
    assert fake_qobuz.api_requests("favorite/getNewReleases") == []
