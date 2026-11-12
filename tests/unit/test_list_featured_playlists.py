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


async def test_featured_playlists_are_a_page_of_playlists(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    page = (await client.call_tool("list_featured_playlists", {})).structured_content
    assert page is not None
    assert [(playlist["id"], playlist["url"]) for playlist in page["items"]] == [
        (201, "https://open.qobuz.com/playlist/201")
    ]
    request = fake_qobuz.api_requests("playlist/getFeatured")[-1]
    assert dict(request.url.params) == {"type": "editor-picks", "limit": "25", "offset": "0"}


async def test_genre_filter_is_sent_as_genre_ids(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await client.call_tool("list_featured_playlists", {"genre_id": 80, "limit": 5, "offset": 5})
    request = fake_qobuz.api_requests("playlist/getFeatured")[-1]
    assert dict(request.url.params) == {
        "type": "editor-picks",
        "genre_ids": "80",
        "limit": "5",
        "offset": "5",
    }
