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


async def get_album(client: Client[Any], **arguments: Any) -> Any:
    result = await client.call_tool("get_album", {"album_id": ALBUM["id"], **arguments})
    return result.structured_content


async def test_get_album_returns_tracklist_and_audio_quality(client: Client[Any]) -> None:
    """AC-CAT-02"""
    album = await get_album(client)
    assert album["id"] == ALBUM["id"]
    assert album["url"] == f"https://open.qobuz.com/album/{ALBUM['id']}"
    assert album["audio_quality"]["bit_depth"] == 24
    assert album["audio_quality"]["sampling_rate_khz"] == 192
    tracks = album["tracks"]
    assert [track["id"] for track in tracks["items"]] == [101, 102]
    assert tracks["items"][1]["audio_quality"]["sampling_rate_khz"] == 96
    assert (tracks["total"], tracks["limit"], tracks["offset"]) == (3, 2, 0)
    for track in tracks["items"]:
        assert track["url"] == f"https://open.qobuz.com/track/{track['id']}"
        assert track["album"] == {"id": ALBUM["id"], "title": ALBUM["title"]}


async def test_get_album_returns_credits_awards_and_booklets(client: Client[Any]) -> None:
    album = await get_album(client)
    assert album["artists"][1] == {
        "id": 12,
        "name": "Synthetic Pianist",
        "roles": ["featured-artist", "piano"],
    }
    assert album["composer"] == {"id": 13, "name": "Synthetic Composer"}
    assert album["label"] == {"id": 21, "name": "Synthetic Label"}
    assert album["release_date"] == "1959-08-17"
    assert album["description"] == "<p>A synthetic description.</p>"
    assert album["awards"] == [
        {
            "name": "Synthetic Award",
            "publication_name": "Synthetic Magazine",
            "awarded_at": "2023-11-14T22:13:20+00:00",
        }
    ]
    assert album["booklets"] == [
        {"name": "Digital booklet", "url": "https://example.invalid/booklet.pdf"}
    ]


async def test_tracklist_is_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await get_album(client)
    await get_album(client, limit=50, offset=50)
    first, second = fake_qobuz.api_requests("album/get")
    assert (first.url.params["limit"], first.url.params["offset"]) == ("25", "0")
    assert (second.url.params["limit"], second.url.params["offset"]) == ("50", "50")


async def test_unknown_album_error_names_the_id(client: Client[Any]) -> None:
    """AC-BEH-08"""
    result = await client.call_tool(
        "get_album", {"album_id": "9999999999999"}, raise_on_error=False
    )
    assert result.is_error
    assert "album_id=9999999999999" in "".join(getattr(b, "text", "") for b in result.content)
