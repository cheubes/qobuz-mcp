from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import AWARD, FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

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


async def test_award_with_its_albums(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    """AC-BEH-04"""
    result = await client.call_tool(
        "get_award", {"award_id": AWARD["id"], "genre_id": 80, "limit": 2, "offset": 6}
    )
    award = result.structured_content
    assert award is not None
    assert (award["id"], award["url"], award["name"]) == (
        6,
        "https://play.qobuz.com/award/6",
        "Synthetic Award",
    )
    assert [album["url"] for album in award["albums"]["items"]] == [
        "https://open.qobuz.com/album/0000000000021",
        "https://open.qobuz.com/album/0000000000022",
    ]
    assert award["albums"]["has_more"] is True
    assert dict(fake_qobuz.api_requests("award/page")[-1].url.params) == {"award_id": "6"}
    assert dict(fake_qobuz.api_requests("award/getAlbums")[-1].url.params) == {
        "award_id": "6",
        "genre_ids": "80",
        "limit": "2",
        "offset": "6",
    }


async def test_unknown_award_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_award", {"award_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "award_id=999" in "".join(getattr(b, "text", "") for b in result.content)
