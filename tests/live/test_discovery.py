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
