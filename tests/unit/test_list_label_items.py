from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.api import LABEL_SECTION_ENDPOINTS
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, LABEL, FakeQobuz

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


async def label_items(client: Client[Any], section: str, **arguments: Any) -> Any:
    result = await client.call_tool(
        "list_label_items", {"label_id": LABEL["id"], "section": section, **arguments}
    )
    return result.structured_content["result"]  # type: ignore[index]


@pytest.mark.parametrize("section", sorted(LABEL_SECTION_ENDPOINTS))
async def test_each_section_requests_its_endpoint(
    client: Client[Any], fake_qobuz: FakeQobuz, section: str
) -> None:
    """AC-CAT-11"""
    await label_items(client, section, limit=4, offset=8)
    request = fake_qobuz.api_requests(LABEL_SECTION_ENDPOINTS[section])[-1]
    assert dict(request.url.params) == {"label_id": "21", "limit": "4", "offset": "8"}
    assert len([r for r in fake_qobuz.requests if r.url.path.startswith("/api.json/")]) == 1


async def test_sections_return_the_matching_items(client: Client[Any]) -> None:
    artists = await label_items(client, "top_artists")
    assert [(a["id"], a["url"]) for a in artists["items"]] == [
        (11, "https://open.qobuz.com/artist/11"),
        (12, "https://open.qobuz.com/artist/12"),
    ]
    assert artists["has_more"] is True
    playlists = await label_items(client, "playlists")
    assert playlists["items"][0]["url"] == "https://open.qobuz.com/playlist/204"
    for section in ("upcoming_releases", "awarded_releases"):
        albums = await label_items(client, section)
        assert albums["items"][0]["url"] == "https://open.qobuz.com/album/0000000000021"


async def test_unknown_section_is_rejected_before_any_request(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    result = await client.call_tool(
        "list_label_items", {"label_id": 21, "section": "stories"}, raise_on_error=False
    )
    assert result.is_error
    assert [r for r in fake_qobuz.requests if r.url.path.startswith("/api.json/")] == []
