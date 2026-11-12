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


async def test_tracks_are_sent_in_the_given_order(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-PL-04"""
    playlist = (
        await client.call_tool(
            "add_tracks_to_playlist", {"playlist_id": 301, "track_ids": [103, 101, 102]}
        )
    ).structured_content
    assert playlist is not None
    assert playlist["id"] == 301
    assert fake_qobuz.form("playlist/addTracks") == {
        "playlist_id": "301",
        "track_ids": "103,101,102",
    }


async def test_an_empty_track_list_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "add_tracks_to_playlist", {"playlist_id": 301, "track_ids": []}, raise_on_error=False
    )
    assert result.is_error
    assert fake_qobuz.api_requests("playlist/addTracks") == []


async def test_add_tracks_to_playlist_is_additive(client: Client[Any]) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "add_tracks_to_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, False)
