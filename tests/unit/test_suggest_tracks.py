import json
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, TRACK, FakeQobuz

pytestmark = pytest.mark.anyio

OTHER_TRACK = {
    **TRACK,
    "id": 102,
    "performer": {"id": 12, "name": "Other Synthetic Artist"},
    "album": {
        "id": "0000000000002",
        "title": "Second Synthetic Album",
        "label": {"id": 21, "name": "Synthetic Label"},
        "genre": {"id": 80, "name": "Jazz"},
    },
}


@pytest.fixture
def fake_qobuz(monkeypatch: pytest.MonkeyPatch) -> FakeQobuz:
    fake = FakeQobuz(other_tracks={102: OTHER_TRACK})
    monkeypatch.setattr(server, "http_client", fake.client)
    return fake


@pytest.fixture
async def client(fake_qobuz: FakeQobuz) -> AsyncIterator[Client[Any]]:
    save_credentials(Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN))
    async with Client(server.mcp) as connected:
        yield connected


async def test_suggestion_request_describes_each_given_track(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    """AC-CAT-09"""
    await client.call_tool("suggest_tracks", {"track_ids": [TRACK["id"], 102], "limit": 3})
    request = fake_qobuz.api_requests("dynamic/suggest")[-1]
    assert request.method == "POST"
    assert request.headers["Content-Type"] == "application/json"
    assert json.loads(request.content) == {
        "limit": 3,
        "listened_tracks_ids": [101, 102],
        "track_to_analysed": [
            {"track_id": 101, "artist_id": 11, "label_id": 0, "genre_id": 0},
            {"track_id": 102, "artist_id": 12, "label_id": 21, "genre_id": 80},
        ],
    }
    assert [r.url.params["track_id"] for r in fake_qobuz.api_requests("track/get")] == [
        "101",
        "102",
    ]


async def test_suggestions_are_one_complete_page_of_tracks(client: Client[Any]) -> None:
    result = await client.call_tool("suggest_tracks", {"track_ids": [TRACK["id"]]})
    page = result.structured_content
    assert page is not None
    assert [(track["id"], track["url"]) for track in page["items"]] == [
        (101, "https://open.qobuz.com/track/101")
    ]
    assert (page["has_more"], page["total"]) == (False, 1)


@pytest.mark.parametrize("track_ids", [[], list(range(1, 12))])
async def test_track_count_is_checked_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz, track_ids: list[int]
) -> None:
    """AC-CAT-10"""
    result = await client.call_tool(
        "suggest_tracks", {"track_ids": track_ids}, raise_on_error=False
    )
    assert result.is_error
    assert [r for r in fake_qobuz.requests if "/api.json/" in str(r.url)] == []


async def test_unknown_track_error_names_the_id(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    result = await client.call_tool("suggest_tracks", {"track_ids": [999]}, raise_on_error=False)
    assert result.is_error
    assert "track_id=999" in "".join(getattr(b, "text", "") for b in result.content)
    assert fake_qobuz.api_requests("dynamic/suggest") == []
