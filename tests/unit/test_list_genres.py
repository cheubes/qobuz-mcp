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


async def list_genres(client: Client[Any], **arguments: Any) -> Any:
    return (await client.call_tool("list_genres", arguments)).structured_content


async def test_top_level_genres_have_an_empty_path(
    client: Client[Any], fake_qobuz: FakeQobuz
) -> None:
    page = await list_genres(client)
    assert page["items"] == [
        {"id": 112, "name": "Pop/Rock", "path": []},
        {"id": 80, "name": "Jazz", "path": []},
    ]
    assert "parent_id" not in fake_qobuz.api_requests("genre/list")[-1].url.params


async def test_sub_genres_list_their_ancestors_from_the_root(client: Client[Any]) -> None:
    assert (await list_genres(client, parent_genre_id=112))["items"] == [
        {"id": 117, "name": "Rock", "path": [112]}
    ]
    assert (await list_genres(client, parent_genre_id=117))["items"] == [
        {"id": 118, "name": "Indie Rock", "path": [112, 117]}
    ]


async def test_genres_are_paginated(client: Client[Any], fake_qobuz: FakeQobuz) -> None:
    await list_genres(client, parent_genre_id=112, limit=5, offset=5)
    request = fake_qobuz.api_requests("genre/list")[-1]
    assert dict(request.url.params) == {"parent_id": "112", "limit": "5", "offset": "5"}
