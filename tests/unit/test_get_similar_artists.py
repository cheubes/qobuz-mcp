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


async def test_similar_artists_are_a_page_of_artists(client: Client[Any]) -> None:
    result = await client.call_tool("get_similar_artists", {"artist_id": ARTIST["id"]})
    page = result.structured_content
    assert page is not None
    assert [(artist["id"], artist["url"]) for artist in page["items"]] == [
        (12, "https://open.qobuz.com/artist/12"),
        (13, "https://open.qobuz.com/artist/13"),
    ]
    assert (page["total"], page["limit"], page["offset"]) == (2, 2, 0)


async def test_similar_artists_are_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await client.call_tool(
        "get_similar_artists", {"artist_id": ARTIST["id"], "limit": 5, "offset": 10}
    )
    request = fake_qobuz.api_requests("artist/getSimilarArtists")[-1]
    assert dict(request.url.params) == {"artist_id": "11", "limit": "5", "offset": "10"}


async def test_unknown_artist_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_similar_artists", {"artist_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "artist_id=999" in "".join(getattr(b, "text", "") for b in result.content)
