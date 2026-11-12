from collections.abc import AsyncIterator
from typing import Any, get_args

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.api import DISCOVER_ALBUM_ENDPOINTS
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
    result = await client.call_tool("list_featured_albums", {"category": "best-sellers"})
    page = result.structured_content
    assert page is not None
    assert [album["id"] for album in page["items"]] == ["0000000000001", "0000000000002"]
    request = fake_qobuz.api_requests("album/getFeatured")[-1]
    assert dict(request.url.params) == {"type": "best-sellers", "limit": "25", "offset": "0"}


async def test_genre_filter_is_sent_as_genre_ids(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await client.call_tool(
        "list_featured_albums",
        {"category": "editor-picks", "genre_id": 80, "limit": 5, "offset": 10},
    )
    request = fake_qobuz.api_requests("album/getFeatured")[-1]
    assert dict(request.url.params) == {
        "type": "editor-picks",
        "genre_ids": "80",
        "limit": "5",
        "offset": "10",
    }


async def test_unknown_category_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_featured_albums", {"category": "not-a-category"}, raise_on_error=False
    )
    assert result.is_error
    assert fake_qobuz.api_requests("album/getFeatured") == []


def test_categories_match_the_technical_specifications() -> None:
    assert len(get_args(FeaturedAlbumCategory)) == 16


@pytest.mark.parametrize("category", get_args(FeaturedAlbumCategory))
async def test_each_category_goes_to_its_endpoint(
    client: Client[Any], fake_qobuz: FakeQobuz, category: str
) -> None:
    """AC-CAT-06"""
    result = await client.call_tool("list_featured_albums", {"category": category, "limit": 2})
    page = result.structured_content
    assert page is not None
    assert page["items"]
    endpoint = DISCOVER_ALBUM_ENDPOINTS.get(category, "album/getFeatured")
    request = fake_qobuz.api_requests(endpoint)[-1]
    expected = {"limit": "2", "offset": "0"}
    if endpoint == "album/getFeatured":
        expected["type"] = category
    assert dict(request.url.params) == expected
    assert len([r for r in fake_qobuz.requests if "/api.json/" in str(r.url)]) == 1


async def test_discover_categories_send_the_genre_filter(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-CAT-06"""
    result = await client.call_tool(
        "list_featured_albums", {"category": "new-releases", "genre_id": 80}
    )
    page = result.structured_content
    assert page is not None
    assert (page["has_more"], page["total"]) == (True, None)
    request = fake_qobuz.api_requests("discover/newReleases")[-1]
    assert dict(request.url.params) == {"genre_ids": "80", "limit": "25", "offset": "0"}
