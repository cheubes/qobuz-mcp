from collections.abc import AsyncIterator
from typing import Any

import httpx2
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


async def get_artist(client: Client[Any], **arguments: Any) -> Any:
    result = await client.call_tool("get_artist", {"artist_id": ARTIST["id"], **arguments})
    return result.structured_content


async def test_get_artist_returns_biography_and_discography(client: Client[Any]) -> None:
    artist = await get_artist(client)
    assert artist["id"] == 11
    assert artist["url"] == "https://open.qobuz.com/artist/11"
    assert artist["albums_count"] == 42
    assert artist["biography_summary"] == "Short."
    assert artist["biography"] is None
    albums = artist["albums"]
    assert [album["id"] for album in albums["items"]] == ["0000000000001", "0000000000002"]
    assert (albums["total"], albums["limit"], albums["offset"]) == (42, 2, 0)


async def test_full_biography_on_request(client: Client[Any]) -> None:
    artist = await get_artist(client, full_biography=True)
    assert artist["biography_summary"] == "Short."
    assert artist["biography"] == "<p>A synthetic biography.</p>"


async def test_discography_is_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await get_artist(client, limit=10, offset=30)
    request = fake_qobuz.api_requests("artist/get")[-1]
    assert dict(request.url.params) == {
        "artist_id": "11",
        "extra": "albums",
        "limit": "10",
        "offset": "30",
    }


async def test_missing_biography_is_null(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    fake_qobuz.api_responses["artist/get"] = httpx2.Response(
        200, json={key: value for key, value in ARTIST.items() if key != "biography"}
    )
    artist = await get_artist(client, full_biography=True)
    assert (artist["biography_summary"], artist["biography"]) == (None, None)


async def test_unknown_artist_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_artist", {"artist_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "artist_id=999" in "".join(getattr(b, "text", "") for b in result.content)
