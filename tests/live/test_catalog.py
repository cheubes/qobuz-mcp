from typing import Any

import pytest
from fastmcp import Client

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_search_finds_albums_of_a_well_known_artist(live_client: Client[Any]) -> None:
    """AC-LIVE-02"""
    result = await live_client.call_tool(
        "search_catalog", {"query": "Miles Davis", "type": "albums", "limit": 5}
    )
    page = result.structured_content["result"]  # type: ignore[index]
    assert page["total"] >= 1
    album = page["items"][0]
    assert album["id"]
    assert album["url"] == f"https://open.qobuz.com/album/{album['id']}"


async def test_get_album_returns_a_tracklist_and_audio_quality(live_client: Client[Any]) -> None:
    """AC-LIVE-03"""
    search = await live_client.call_tool(
        "search_catalog", {"query": "Miles Davis Kind of Blue", "type": "albums", "limit": 1}
    )
    album_id = search.structured_content["result"]["items"][0]["id"]  # type: ignore[index]
    result = await live_client.call_tool("get_album", {"album_id": album_id})
    album = result.structured_content
    assert album is not None
    assert album["tracks"]["items"]
    assert album["tracks"]["total"] >= len(album["tracks"]["items"])
    assert album["audio_quality"]["bit_depth"]
    assert album["audio_quality"]["sampling_rate_khz"]


async def test_featured_playlists_for_a_tag(live_client: Client[Any]) -> None:
    """AC-LIVE-07"""
    result = await live_client.call_tool("list_featured_playlists", {"tag": "hi-res", "limit": 3})
    page = result.structured_content
    assert page is not None
    assert page["items"]
    playlist = page["items"][0]
    assert playlist["url"] == f"https://open.qobuz.com/playlist/{playlist['id']}"
