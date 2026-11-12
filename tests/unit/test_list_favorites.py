from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, FAVORITES, FakeQobuz

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


async def list_favorites(client: Client[Any], **arguments: Any) -> Any:
    result = await client.call_tool("list_favorites", arguments)
    return result.structured_content["result"]  # type: ignore[index]


@pytest.mark.parametrize("kind", ["albums", "artists", "tracks"])
async def test_favorites_contain_only_the_requested_type(
    client: Client[Any], fake_qobuz: FakeQobuz, kind: str
) -> None:
    """AC-LIB-01"""
    page = await list_favorites(client, type=kind)
    expected_ids = [item["id"] for item in FAVORITES[kind]["items"]]
    assert [favorite["item"]["id"] for favorite in page["items"]] == [
        str(item_id) if kind == "albums" else item_id for item_id in expected_ids
    ]
    singular = kind.removesuffix("s")
    assert all(
        favorite["item"]["url"].startswith(f"https://open.qobuz.com/{singular}/")
        for favorite in page["items"]
    )
    assert fake_qobuz.api_requests("favorite/getUserFavorites")[-1].url.params["type"] == kind


async def test_favorites_carry_their_date_in_qobuz_order(client: Client[Any]) -> None:
    """AC-LIB-05"""
    page = await list_favorites(client, type="albums")
    assert [favorite["favorited_at"] for favorite in page["items"]] == [
        "2023-11-14T22:13:20+00:00",
        "2023-11-13T22:13:20+00:00",
    ]


async def test_favorites_are_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await list_favorites(client, type="tracks", limit=10, offset=20)
    request = fake_qobuz.api_requests("favorite/getUserFavorites")[-1]
    assert dict(request.url.params) == {"type": "tracks", "limit": "10", "offset": "20"}
