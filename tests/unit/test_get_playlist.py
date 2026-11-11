from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, PLAYLIST, FakeQobuz

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


async def get_playlist(client: Client[Any], **arguments: Any) -> Any:
    result = await client.call_tool("get_playlist", {"playlist_id": PLAYLIST["id"], **arguments})
    return result.structured_content


async def test_entries_carry_both_track_and_playlist_track_ids(client: Client[Any]) -> None:
    """AC-CAT-04"""
    entries = (await get_playlist(client))["entries"]["items"]
    assert [(entry["playlist_track_id"], entry["track"]["id"]) for entry in entries] == [
        (5001, 101),
        (5002, 102),
        (5003, 101),
    ]
    assert [entry["position"] for entry in entries] == [1, 2, 3]


async def test_get_playlist_returns_its_details(client: Client[Any]) -> None:
    playlist = await get_playlist(client)
    assert playlist["url"] == "https://open.qobuz.com/playlist/201"
    assert playlist["owner"] == {"id": 31, "name": "Synthetic Owner"}
    assert playlist["genres"] == [{"id": 80, "name": "Jazz"}]
    assert playlist["description"] == PLAYLIST["description"]
    entry = playlist["entries"]["items"][0]
    assert entry["track"]["url"] == "https://open.qobuz.com/track/101"
    assert entry["track"]["album"] == {"id": "0000000000001", "title": "First Synthetic Album"}
    assert (playlist["entries"]["total"], playlist["entries"]["limit"]) == (3, 25)


async def test_entries_are_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await get_playlist(client, limit=10, offset=20)
    request = fake_qobuz.api_requests("playlist/get")[-1]
    assert dict(request.url.params) == {
        "playlist_id": "201",
        "extra": "tracks",
        "limit": "10",
        "offset": "20",
    }


async def test_unknown_playlist_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_playlist", {"playlist_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "playlist_id=999" in "".join(getattr(b, "text", "") for b in result.content)
