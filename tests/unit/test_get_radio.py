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


@pytest.mark.parametrize(
    ("seed_type", "seed_id"), [("album", "0000000000021"), ("artist", "11"), ("track", "3001")]
)
async def test_radio_matches_the_seed_type(
    client: Client[Any], fake_qobuz: FakeQobuz, seed_type: str, seed_id: str
) -> None:
    """AC-CAT-08"""
    result = await client.call_tool("get_radio", {"seed_type": seed_type, "seed_id": seed_id})
    assert result.structured_content is not None
    request = fake_qobuz.api_requests(f"radio/{seed_type}")[-1]
    assert dict(request.url.params) == {f"{seed_type}_id": seed_id}
    radio_requests = [r for r in fake_qobuz.requests if "/radio/" in r.url.path]
    assert len(radio_requests) == 1


async def test_radio_is_one_complete_page_of_tracks(client: Client[Any]) -> None:
    result = await client.call_tool("get_radio", {"seed_type": "album", "seed_id": "x"})
    page = result.structured_content
    assert page is not None
    assert [(track["id"], track["url"]) for track in page["items"]] == [
        (3001, "https://open.qobuz.com/track/3001"),
        (3002, "https://open.qobuz.com/track/3002"),
    ]
    first = page["items"][0]
    assert first["performer"] == {"id": 11, "name": "Synthetic Artist"}
    assert first["album"] == {"id": "0000000000021", "title": "First Label Album"}
    assert (first["track_number"], first["audio_quality"]["hires"]) == (2, True)
    assert (page["has_more"], page["total"], page["offset"]) == (False, 2, 0)


async def test_unknown_seed_type_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "get_radio", {"seed_type": "label", "seed_id": "1"}, raise_on_error=False
    )
    assert result.is_error
    assert [r for r in fake_qobuz.requests if "/radio/" in r.url.path] == []
