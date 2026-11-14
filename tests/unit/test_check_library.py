import json
from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, PURCHASE_IDS, FakeQobuz

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


async def check(client: Client[Any], **arguments: Any) -> Any:
    return (await client.call_tool("check_library", arguments)).structured_content


async def test_each_id_is_checked_against_favorites_and_purchases(client: Client[Any]) -> None:
    """AC-LIB-06"""
    status = await check(
        client,
        album_ids=["0000000000021", "0000000000001", "0000000000099"],
        artist_ids=[12, 11],
        track_ids=[3002, 3001],
    )
    assert status == {
        "albums": [
            {"id": "0000000000021", "favorite": True, "purchased": True},
            {"id": "0000000000001", "favorite": True, "purchased": False},
            {"id": "0000000000099", "favorite": False, "purchased": False},
        ],
        "artists": [
            {"id": 12, "favorite": False, "purchased": None},
            {"id": 11, "favorite": True, "purchased": None},
        ],
        "tracks": [
            {"id": 3002, "favorite": False, "purchased": True},
            {"id": 3001, "favorite": True, "purchased": False},
        ],
    }


async def test_artists_only_need_no_purchase_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-LIB-06"""
    status = await check(client, artist_ids=[11])
    assert status["artists"] == [{"id": 11, "favorite": True, "purchased": None}]
    assert fake_qobuz.api_requests("purchase/getUserPurchasesIds") == []


async def test_no_id_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-LIB-07"""
    result = await client.call_tool("check_library", {}, raise_on_error=False)
    assert result.is_error
    assert [r for r in fake_qobuz.requests if r.url.path.startswith("/api.json/")] == []


async def test_account_login_never_reaches_the_result(client: Client[Any]) -> None:
    """AC-LIB-08"""
    result = await client.call_tool("check_library", {"album_ids": ["0000000000021"]})
    login = PURCHASE_IDS["user"]["login"]
    assert login not in json.dumps(result.structured_content)
    assert all(login not in getattr(block, "text", "") for block in result.content)


async def test_an_incomplete_purchase_list_leaves_unlisted_items_unknown(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-LIB-10"""
    fake_qobuz.api_responses["purchase/getUserPurchasesIds"] = httpx2.Response(
        200,
        json={
            "albums": {"total": 2, "items": [{"id": "0000000000021"}]},
            "tracks": {"total": 1, "items": [3002]},
        },
    )
    status = await check(
        client, album_ids=["0000000000021", "0000000000099"], track_ids=[3002, 3001]
    )
    assert [album["purchased"] for album in status["albums"]] == [True, None]
    assert [track["purchased"] for track in status["tracks"]] == [True, False]
