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
