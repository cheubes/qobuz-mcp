from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

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


@pytest.mark.parametrize("insert_before", [0, 2])
async def test_entries_and_target_position_are_sent(
    client: Client[Any], fake_qobuz: FakeQobuz, insert_before: int
) -> None:
    """AC-PL-06"""
    await client.call_tool(
        "move_playlist_tracks",
        {"playlist_id": 201, "playlist_track_ids": [5003, 5001], "insert_before": insert_before},
    )
    assert fake_qobuz.form("playlist/updateTracksPosition") == {
        "playlist_id": "201",
        "playlist_track_ids": "5003,5001",
        "insert_before": str(insert_before),
    }


async def test_negative_position_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "move_playlist_tracks",
        {"playlist_id": 201, "playlist_track_ids": [5001], "insert_before": -1},
        raise_on_error=False,
    )
    assert result.is_error
    assert fake_qobuz.api_requests("playlist/updateTracksPosition") == []


async def test_move_playlist_tracks_is_destructive(client: Client[Any]) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "move_playlist_tracks")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, True)
