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


async def test_follow_playlist_sends_its_id(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    result = await client.call_tool("follow_playlist", {"playlist_id": 201})
    assert result.structured_content == {"status": "success"}
    assert fake_qobuz.form("playlist/subscribe") == {"playlist_id": "201"}


async def test_follow_playlist_is_additive(client: Client[Any]) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "follow_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, False)
