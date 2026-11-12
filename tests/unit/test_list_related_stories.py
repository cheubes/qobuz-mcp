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
    ("entity_type", "entity_id"),
    [
        ("album", "0000000000021"),
        ("artist", "11"),
        ("label", "21"),
        ("playlist", "202"),
        ("award", "6"),
    ],
)
async def test_each_entity_type_requests_its_story_endpoint(
    client: Client[Any], fake_qobuz: FakeQobuz, entity_type: str, entity_id: str
) -> None:
    """AC-CAT-11"""
    result = await client.call_tool(
        "list_related_stories",
        {"entity_type": entity_type, "entity_id": entity_id, "limit": 3, "offset": 6},
    )
    page = result.structured_content
    assert page is not None
    assert page["items"][0]["url"].startswith("https://play.qobuz.com/story/")
    assert (page["has_more"], page["total"]) == (True, None)
    request = fake_qobuz.api_requests(f"{entity_type}/story")[-1]
    assert dict(request.url.params) == {
        f"{entity_type}_id": entity_id,
        "limit": "3",
        "offset": "6",
    }
    assert len([r for r in fake_qobuz.requests if r.url.path.startswith("/api.json/")]) == 1


async def test_unknown_entity_type_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_related_stories", {"entity_type": "track", "entity_id": "1"}, raise_on_error=False
    )
    assert result.is_error
    assert [r for r in fake_qobuz.requests if r.url.path.startswith("/api.json/")] == []
