from collections.abc import AsyncIterator
from typing import Any

import httpx2
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


async def test_delete_playlist_sends_only_its_id(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("delete_playlist", {"playlist_id": 301})
    assert result.structured_content == {"status": "success"}
    assert fake_qobuz.form("playlist/delete") == {"playlist_id": "301"}


async def test_deleting_a_playlist_not_owned_is_reported(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    fake_qobuz.api_responses["playlist/delete"] = httpx2.Response(403, json={"code": 403})
    result = await client.call_tool("delete_playlist", {"playlist_id": 201}, raise_on_error=False)
    assert result.is_error
    assert "not owned by the user" in "".join(getattr(b, "text", "") for b in result.content)


async def test_delete_playlist_is_destructive(client: Client[Any]) -> None:
    tool = next(t for t in await client.list_tools() if t.name == "delete_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, True)
