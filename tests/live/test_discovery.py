from typing import Any

import pytest
from fastmcp import Client

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def first_album(live_client: Client[Any]) -> dict[str, Any]:
    search = await live_client.call_tool(
        "search_catalog", {"query": "Miles Davis Kind of Blue", "type": "albums", "limit": 1}
    )
    return search.structured_content["result"]["items"][0]  # type: ignore[index,no-any-return]


async def test_list_similar_albums(live_client: Client[Any]) -> None:
    """AC-LIVE-09"""
    album = await first_album(live_client)
    result = await live_client.call_tool("list_similar_albums", {"album_id": album["id"]})
    page = result.structured_content
    assert page is not None
    assert page["has_more"] is False
    assert all(item["url"].startswith("https://open.qobuz.com/album/") for item in page["items"])


async def test_get_radio(live_client: Client[Any]) -> None:
    """AC-LIVE-09"""
    album = await first_album(live_client)
    for seed_type, seed_id in (("album", album["id"]), ("artist", str(album["artist"]["id"]))):
        result = await live_client.call_tool(
            "get_radio", {"seed_type": seed_type, "seed_id": seed_id}
        )
        page = result.structured_content
        assert page is not None
        assert page["items"]
        assert page["items"][0]["url"].startswith("https://open.qobuz.com/track/")


async def test_list_artist_playlists(live_client: Client[Any]) -> None:
    """AC-LIVE-09"""
    album = await first_album(live_client)
    result = await live_client.call_tool(
        "list_artist_playlists", {"artist_id": album["artist"]["id"], "limit": 3}
    )
    page = result.structured_content
    assert page is not None
    assert isinstance(page["has_more"], bool)
    assert all(item["url"].startswith("https://open.qobuz.com/playlist/") for item in page["items"])


@pytest.mark.parametrize(
    "section", ["top_artists", "upcoming_releases", "playlists", "awarded_releases"]
)
async def test_list_label_items(live_client: Client[Any], section: str) -> None:
    """AC-LIVE-09"""
    album = await first_album(live_client)
    result = await live_client.call_tool(
        "list_label_items", {"label_id": album["label"]["id"], "section": section, "limit": 3}
    )
    page = result.structured_content["result"]  # type: ignore[index]
    assert isinstance(page["has_more"], bool)
    assert all(item["url"].startswith("https://open.qobuz.com/") for item in page["items"])


async def test_list_awards(live_client: Client[Any]) -> None:
    """AC-LIVE-09"""
    result = await live_client.call_tool("list_awards", {"limit": 3})
    page = result.structured_content
    assert page is not None
    assert page["items"]
    award = page["items"][0]
    assert award["url"] == f"https://play.qobuz.com/award/{award['id']}"
