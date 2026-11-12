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


async def test_add_favorites_sends_every_id_in_one_call(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-LIB-02"""
    result = await client.call_tool(
        "add_favorites",
        {"album_ids": ["0000000000001", "0000000000002"], "artist_ids": [11], "track_ids": [101]},
    )
    assert result.structured_content == {"status": "success"}
    assert len(fake_qobuz.api_requests("favorite/create")) == 1
    assert fake_qobuz.form("favorite/create") == {
        "album_ids": "0000000000001,0000000000002",
        "artist_ids": "11",
        "track_ids": "101",
    }


async def test_one_kind_of_id_is_enough(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await client.call_tool("add_favorites", {"track_ids": [101, 102]})
    assert fake_qobuz.form("favorite/create") == {"track_ids": "101,102"}


@pytest.mark.parametrize("arguments", [{}, {"album_ids": [], "artist_ids": [], "track_ids": []}])
async def test_no_id_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz, arguments: dict[str, list[Any]]
) -> None:
    """AC-LIB-03"""
    result = await client.call_tool("add_favorites", arguments, raise_on_error=False)
    assert result.is_error
    assert "at least one" in "".join(getattr(b, "text", "") for b in result.content)
    assert fake_qobuz.api_requests("favorite/create") == []


async def test_add_favorites_is_additive(client: Client[Any]) -> None:
    tool = next(tool for tool in await client.list_tools() if tool.name == "add_favorites")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, False)
