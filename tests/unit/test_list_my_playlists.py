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


@pytest.mark.parametrize(("choice", "sent"), [("owned", "owner"), ("followed", "subscriber")])
async def test_filter_requests_only_those_playlists(
    client: Client[Any], fake_qobuz: FakeQobuz, choice: str, sent: str
) -> None:
    """AC-LIB-04"""
    await client.call_tool("list_my_playlists", {"filter": choice})
    request = fake_qobuz.api_requests("playlist/getUserPlaylists")[-1]
    assert request.url.params["filter"] == sent


async def test_no_filter_lists_owned_and_followed_playlists(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    page = (await client.call_tool("list_my_playlists", {})).structured_content
    assert page is not None
    assert [playlist["id"] for playlist in page["items"]] == [201]
    request = fake_qobuz.api_requests("playlist/getUserPlaylists")[-1]
    assert dict(request.url.params) == {"limit": "25", "offset": "0"}


async def test_unknown_filter_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("list_my_playlists", {"filter": "owner"}, raise_on_error=False)
    assert result.is_error
    assert fake_qobuz.api_requests("playlist/getUserPlaylists") == []
