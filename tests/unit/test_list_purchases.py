from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
from qobuz_mcp.credentials import Credentials, save_credentials
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, SEARCH_RESULTS, FakeQobuz

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


@pytest.mark.parametrize("kind", ["albums", "tracks"])
async def test_purchases_contain_only_the_requested_type(
    client: Client[Any], fake_qobuz: FakeQobuz, kind: str
) -> None:
    """AC-LIB-01"""
    result = await client.call_tool("list_purchases", {"type": kind})
    page = result.structured_content["result"]  # type: ignore[index]
    expected = [item["id"] for item in SEARCH_RESULTS[kind]["items"]]
    assert [item["id"] for item in page["items"]] == [
        str(item_id) if kind == "albums" else item_id for item_id in expected
    ]
    singular = kind.removesuffix("s")
    assert all(
        item["url"].startswith(f"https://open.qobuz.com/{singular}/") for item in page["items"]
    )
    request = fake_qobuz.api_requests("purchase/getUserPurchases")[-1]
    assert dict(request.url.params) == {"type": kind, "limit": "25", "offset": "0"}


async def test_artists_are_not_a_purchase_type(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    result = await client.call_tool("list_purchases", {"type": "artists"}, raise_on_error=False)
    assert result.is_error
    assert fake_qobuz.api_requests("purchase/getUserPurchases") == []
