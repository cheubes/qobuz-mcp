from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import ALBUM, FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

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


async def test_similar_albums_are_one_complete_page(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("list_similar_albums", {"album_id": ALBUM["id"]})
    page = result.structured_content
    assert page is not None
    assert [(album["id"], album["url"]) for album in page["items"]] == [
        ("0000000000021", "https://open.qobuz.com/album/0000000000021"),
        ("0000000000022", "https://open.qobuz.com/album/0000000000022"),
    ]
    assert (page["has_more"], page["total"], page["limit"], page["offset"]) == (False, 2, 2, 0)
    request = fake_qobuz.api_requests("album/suggest")[-1]
    assert dict(request.url.params) == {"album_id": ALBUM["id"]}


async def test_unknown_album_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool(
        "list_similar_albums", {"album_id": "unknown"}, raise_on_error=False
    )
    assert result.is_error
    assert "album_id=unknown" in "".join(getattr(b, "text", "") for b in result.content)
