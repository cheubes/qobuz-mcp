from collections.abc import AsyncIterator
from typing import Any

import httpx2
import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from qobuz_mcp.models import biography_excerpt
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
    assert artist["name"] == "Synthetic Artist"
    assert artist["albums_count"] is None
    albums = artist["albums"]
    assert [album["id"] for album in albums["items"]] == ["0000000000031", "0000000000032"]
    assert albums["items"][0]["artist"]["name"] == "Synthetic Artist"
    assert (albums["has_more"], albums["total"], albums["limit"], albums["offset"]) == (
        True,
        None,
        25,
        0,
    )


async def test_biography_is_an_excerpt_by_default(client: Client[Any]) -> None:
    """AC-CAT-05"""
    artist = await get_artist(client)
    full_text = ARTIST["biography"]["content"]
    assert len(full_text) > 1000
    assert artist["biography_truncated"] is True
    assert len(artist["biography"]) <= 1000
    assert full_text.startswith(artist["biography"])
    assert artist["biography"].endswith(".")


async def test_full_biography_on_request(client: Client[Any]) -> None:
    """AC-CAT-05"""
    artist = await get_artist(client, full_biography=True)
    assert artist["biography"] == ARTIST["biography"]["content"]
    assert artist["biography_truncated"] is False


@pytest.mark.parametrize(
    ("text", "excerpt", "truncated"),
    [
        ("Short text.", "Short text.", False),
        ("a" * 1000, "a" * 1000, False),
        ("First! " + "b" * 995 + " end", "First!", True),
        ("Why? " + "c" * 990 + " d. " + "e" * 10, "Why? " + "c" * 990 + " d.", True),
        ("word " * 300, ("word " * 200).rstrip(), True),
        ("x" * 1200, "x" * 1000, True),
    ],
)
def test_biography_excerpt_cuts_at_a_sentence_end(text: str, excerpt: str, truncated: bool) -> None:
    """AC-CAT-05"""
    assert biography_excerpt(text) == (excerpt, truncated)
    assert text.startswith(excerpt)


async def test_discography_is_paginated_and_filtered(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await get_artist(client, release_type="live", limit=10, offset=30)
    page_request = fake_qobuz.api_requests("artist/page")[-1]
    assert dict(page_request.url.params) == {"artist_id": "11", "sort": "relevant"}
    request = fake_qobuz.api_requests("artist/getReleasesList")[-1]
    assert dict(request.url.params) == {
        "artist_id": "11",
        "release_type": "live",
        "sort": "release_date",
        "limit": "10",
        "offset": "30",
    }
    assert fake_qobuz.api_requests("artist/get") == []


async def test_whole_discography_without_release_type(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    await get_artist(client)
    request = fake_qobuz.api_requests("artist/getReleasesList")[-1]
    assert "release_type" not in request.url.params


async def test_missing_biography_is_null(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    fake_qobuz.api_responses["artist/page"] = httpx2.Response(
        200, json={key: value for key, value in ARTIST.items() if key != "biography"}
    )
    artist = await get_artist(client)
    assert (artist["biography"], artist["biography_truncated"]) == (None, False)


async def test_unknown_artist_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_artist", {"artist_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "artist_id=999" in "".join(getattr(b, "text", "") for b in result.content)
