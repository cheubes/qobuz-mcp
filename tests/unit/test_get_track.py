from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, TRACK, FakeQobuz

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


async def get_track(client: Client[Any]) -> Any:
    result = await client.call_tool("get_track", {"track_id": TRACK["id"]})
    return result.structured_content


async def test_get_track_returns_performers_and_credits(client: Client[Any]) -> None:
    """AC-CAT-03"""
    track = await get_track(client)
    assert track["performer"] == {"id": 11, "name": "Synthetic Artist"}
    assert track["credits"] == TRACK["performers"]
    assert track["composer"] == {"id": 13, "name": "Synthetic Composer"}


async def test_get_track_returns_its_details(client: Client[Any]) -> None:
    track = await get_track(client)
    assert track["id"] == 101
    assert track["url"] == "https://open.qobuz.com/track/101"
    assert track["album"] == {"id": "0000000000001", "title": "First Synthetic Album"}
    assert track["isrc"] == "ZZ0000000001"
    assert track["release_date"] == "1959-08-17"
    assert track["duration_seconds"] == 545
    assert track["audio_quality"] == {
        "bit_depth": 24,
        "sampling_rate_khz": 192,
        "channels": 2,
        "hires": True,
    }


async def test_missing_credits_are_null(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    """AC-CAT-03"""
    for key in ("performers", "performer", "composer"):
        del fake_qobuz.track[key]
    track = await get_track(client)
    assert (track["credits"], track["performer"], track["composer"]) == (None, None, None)


async def test_unknown_track_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_track", {"track_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "track_id=999" in "".join(getattr(b, "text", "") for b in result.content)


async def test_track_id_must_be_positive(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    result = await client.call_tool("get_track", {"track_id": 0}, raise_on_error=False)
    assert result.is_error
    assert fake_qobuz.api_requests("track/get") == []
