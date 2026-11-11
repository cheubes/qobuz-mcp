from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server
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


async def test_get_label_returns_description_and_albums(client: Client[Any]) -> None:
    result = await client.call_tool("get_label", {"label_id": LABEL["id"]})
    label = result.structured_content
    assert label is not None
    assert (label["id"], label["url"], label["name"]) == (
        21,
        "https://open.qobuz.com/label/21",
        "Synthetic Label",
    )
    assert label["description"] == "A synthetic label description."
    assert [album["id"] for album in label["albums"]["items"]] == [
        "0000000000001",
        "0000000000002",
    ]
    assert label["albums"]["total"] == 120


async def test_label_albums_are_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await client.call_tool("get_label", {"label_id": LABEL["id"], "limit": 10, "offset": 40})
    request = fake_qobuz.api_requests("label/get")[-1]
    assert dict(request.url.params) == {
        "label_id": "21",
        "extra": "albums",
        "limit": "10",
        "offset": "40",
    }


async def test_unknown_label_error_names_the_id(client: Client[Any]) -> None:
    result = await client.call_tool("get_label", {"label_id": 999}, raise_on_error=False)
    assert result.is_error
    assert "label_id=999" in "".join(getattr(b, "text", "") for b in result.content)
