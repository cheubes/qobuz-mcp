from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import ARTIST, FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

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


async def test_artist_playlists_are_a_page_of_playlists(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_artist_playlists", {"artist_id": ARTIST["id"], "limit": 5, "offset": 10}
    )
    page = result.structured_content
    assert page is not None
    playlist = page["items"][0]
    assert (playlist["id"], playlist["url"], playlist["name"]) == (
        203,
        "https://open.qobuz.com/playlist/203",
        "Synthetic Artist Essentials",
    )
    assert (page["has_more"], page["total"]) == (False, None)
    request = fake_qobuz.api_requests("artist/playlists")[-1]
    assert dict(request.url.params) == {"artist_id": "11", "limit": "5", "offset": "10"}


async def test_unknown_artist_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool(
        "list_artist_playlists", {"artist_id": 999}, raise_on_error=False
    )
    assert result.is_error
    assert "artist_id=999" in "".join(getattr(b, "text", "") for b in result.content)
