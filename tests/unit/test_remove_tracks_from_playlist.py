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


async def test_only_the_targeted_entry_of_a_duplicated_track_is_sent(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-PL-05"""
    entries = PLAYLIST["tracks"]["items"]
    duplicates = [entry for entry in entries if entry["id"] == 101]
    assert len(duplicates) == 2
    target = duplicates[1]["playlist_track_id"]
    await client.call_tool(
        "remove_tracks_from_playlist",
        {"playlist_id": PLAYLIST["id"], "playlist_track_ids": [target]},
    )
    assert fake_qobuz.form("playlist/deleteTracks") == {
        "playlist_id": str(PLAYLIST["id"]),
        "playlist_track_ids": str(target),
    }


async def test_an_empty_entry_list_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "remove_tracks_from_playlist",
        {"playlist_id": 201, "playlist_track_ids": []},
        raise_on_error=False,
    )
    assert result.is_error
    assert fake_qobuz.api_requests("playlist/deleteTracks") == []


async def test_remove_tracks_from_playlist_is_destructive(client: Client[Any]) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "remove_tracks_from_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, True)
    assert (
        "playlist_track_id" in tool.input_schema["properties"]["playlist_track_ids"]["description"]
    )
