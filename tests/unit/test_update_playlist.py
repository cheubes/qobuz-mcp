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


async def test_only_the_given_fields_are_sent(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    """AC-PL-02"""
    playlist = (
        await client.call_tool("update_playlist", {"playlist_id": 301, "description": "New"})
    ).structured_content
    assert playlist is not None
    assert playlist["id"] == 301
    assert fake_qobuz.form("playlist/update") == {"playlist_id": "301", "description": "New"}


async def test_visibility_can_be_changed_alone(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    """AC-PL-02"""
    await client.call_tool("update_playlist", {"playlist_id": 301, "is_public": False})
    assert fake_qobuz.form("playlist/update") == {"playlist_id": "301", "is_public": "false"}


async def test_nothing_to_change_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-PL-03"""
    result = await client.call_tool("update_playlist", {"playlist_id": 301}, raise_on_error=False)
    assert result.is_error
    assert "at least one field" in "".join(getattr(b, "text", "") for b in result.content)
    assert fake_qobuz.api_requests("playlist/update") == []


async def test_playlist_not_owned_is_reported_without_secrets(
    client: Client[Any],
    fake_qobuz: FakeQobuz,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-BEH-09, AC-BEH-11"""
    fake_qobuz.api_responses["playlist/update"] = httpx2.Response(
        403, json={"status": "error", "code": 403, "message": "Forbidden"}
    )
    result = await client.call_tool(
        "update_playlist", {"playlist_id": 201, "name": "Mine now"}, raise_on_error=False
    )
    assert result.is_error
    message = "".join(getattr(b, "text", "") for b in result.content)
    assert "playlist_id=201" in message
    assert "not owned by the user" in message
    captured = capsys.readouterr()
    assert FAKE_TOKEN not in message + captured.out + captured.err + caplog.text


async def test_update_playlist_is_destructive(client: Client[Any]) -> None:
    tool = next(tool for tool in await client.list_tools() if tool.name == "update_playlist")
    assert tool.annotations is not None
    assert (tool.annotations.read_only_hint, tool.annotations.destructive_hint) == (False, True)
