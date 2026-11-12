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
