from typing import Any

import pytest
from fastmcp import Client

pytestmark = [pytest.mark.live, pytest.mark.anyio]


@pytest.mark.parametrize("kind", ["albums", "artists", "tracks"])
async def test_list_favorites_returns_a_page(live_client: Client[Any], kind: str) -> None:
    """AC-LIVE-04"""
    result = await live_client.call_tool("list_favorites", {"type": kind, "limit": 1})
    page = result.structured_content["result"]  # type: ignore[index]
    assert page["total"] >= 0
    assert len(page["items"]) <= 1


@pytest.mark.parametrize("arguments", [{}, {"filter": "owned"}, {"filter": "followed"}])
async def test_list_my_playlists_returns_a_page(
    live_client: Client[Any], arguments: dict[str, str]
) -> None:
    """AC-LIVE-04"""
    result = await live_client.call_tool("list_my_playlists", {**arguments, "limit": 1})
    page = result.structured_content
    assert page is not None
    assert page["total"] >= 0
    assert len(page["items"]) <= 1


@pytest.mark.parametrize("source", ["artists", "labels", "awards"])
async def test_list_new_releases_from_favorites(live_client: Client[Any], source: str) -> None:
    """AC-LIVE-10"""
    result = await live_client.call_tool(
        "list_new_releases_from_favorites", {"source": source, "limit": 2}
    )
    page = result.structured_content
    assert page is not None
    assert isinstance(page["has_more"], bool)
    assert len(page["items"]) <= 2


async def test_check_library(live_client: Client[Any]) -> None:
    """AC-LIVE-10"""
    favorites = await live_client.call_tool("list_favorites", {"type": "albums", "limit": 1})
    items = favorites.structured_content["result"]["items"]  # type: ignore[index]
    album_ids = [items[0]["item"]["id"]] if items else ["0000000000000"]
    result = await live_client.call_tool(
        "check_library", {"album_ids": album_ids, "artist_ids": [1]}
    )
    status = result.structured_content
    assert status is not None
    assert [album["id"] for album in status["albums"]] == album_ids
    assert status["albums"][0]["favorite"] is bool(items)
    assert status["artists"][0]["purchased"] is None
