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


async def test_awards_are_a_page_with_their_publication(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool("list_awards", {"limit": 2, "offset": 4})
    page = result.structured_content
    assert page is not None
    assert [(a["name"], a["publication_name"]) for a in page["items"]] == [
        ("Synthetic Award", "Synthetic Magazine"),
        ("Another Synthetic Award", None),
    ]
    assert (page["has_more"], page["total"]) == (True, None)
    request = fake_qobuz.api_requests("award/explore")[-1]
    assert dict(request.url.params) == {"limit": "2", "offset": "4"}


async def test_awards_link_to_their_web_player_page(client: Client[Any]) -> None:
    """AC-BEH-04"""
    page = (await client.call_tool("list_awards", {})).structured_content
    assert page is not None
    for award in page["items"]:
        assert award["url"] == f"https://play.qobuz.com/award/{award['id']}"
