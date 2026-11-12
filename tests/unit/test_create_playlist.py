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


async def test_create_playlist_returns_its_id_and_url(client: Client[Any]) -> None:
    """AC-PL-01"""
    playlist = (await client.call_tool("create_playlist", {"name": "Road trip"})).structured_content
    assert playlist is not None
    assert (playlist["id"], playlist["url"]) == (301, "https://open.qobuz.com/playlist/301")


async def test_new_playlists_are_private_and_non_collaborative_by_default(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-PL-07"""
    await client.call_tool("create_playlist", {"name": "Road trip"})
    assert fake_qobuz.form("playlist/create") == {
        "name": "Road trip",
        "description": "",
        "is_public": "false",
        "is_collaborative": "false",
    }


async def test_visibility_follows_an_explicit_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await client.call_tool(
        "create_playlist",
        {
            "name": "Shared",
            "description": "For friends",
            "is_public": True,
            "is_collaborative": True,
        },
    )
    form = fake_qobuz.form("playlist/create")
    assert (form["description"], form["is_public"], form["is_collaborative"]) == (
        "For friends",
        "true",
        "true",
    )


async def test_empty_name_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("create_playlist", {"name": ""}, raise_on_error=False)
    assert result.is_error
    assert fake_qobuz.api_requests("playlist/create") == []


async def test_create_playlist_is_additive(client: Client[Any]) -> None:
    tool = next(tool for tool in await client.list_tools() if tool.name == "create_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, False)
