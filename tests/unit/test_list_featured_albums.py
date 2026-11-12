from collections.abc import AsyncIterator
from typing import Any, get_args

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from qobuz_mcp.tools.catalog import FeaturedAlbumCategory
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


async def test_featured_albums_are_a_page_of_albums(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("list_featured_albums", {"category": "press-awards"})
    page = result.structured_content
    assert page is not None
    assert [album["id"] for album in page["items"]] == ["0000000000001", "0000000000002"]
    request = fake_qobuz.api_requests("album/getFeatured")[-1]
    assert dict(request.url.params) == {"type": "press-awards", "limit": "25", "offset": "0"}


async def test_genre_filter_is_sent_as_genre_ids(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await client.call_tool(
        "list_featured_albums",
        {"category": "new-releases", "genre_id": 80, "limit": 5, "offset": 10},
    )
    request = fake_qobuz.api_requests("album/getFeatured")[-1]
    assert dict(request.url.params) == {
        "type": "new-releases",
        "genre_ids": "80",
        "limit": "5",
        "offset": "10",
    }


async def test_unknown_category_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_featured_albums", {"category": "album-of-the-week"}, raise_on_error=False
    )
    assert result.is_error
    assert fake_qobuz.api_requests("album/getFeatured") == []


def test_categories_match_the_technical_specifications() -> None:
    assert len(get_args(FeaturedAlbumCategory)) == 15
