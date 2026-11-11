from typing import Any

import httpx2
import pytest

from qobuz_mcp.api import API_BASE_URL, QobuzClient
from qobuz_mcp.errors import AuthenticationError, QobuzApiError
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, FakeQobuz


def client_answering(handler: Any) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


@pytest.mark.anyio
async def test_get_user_sends_the_app_id_and_token_headers() -> None:
    fake = FakeQobuz()
    async with fake.client() as http:
        user = await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get_user()
    assert user["display_name"] == "Test User"
    request = fake.requests[0]
    assert str(request.url).startswith(API_BASE_URL + "user/get")
    assert request.headers["X-App-Id"] == FAKE_APP_ID
    assert request.headers["X-User-Auth-Token"] == FAKE_TOKEN


@pytest.mark.anyio
async def test_authenticated_call_without_token_is_refused_locally() -> None:
    fake = FakeQobuz()
    async with fake.client() as http:
        with pytest.raises(AuthenticationError, match="Not logged in"):
            await QobuzClient(http, FAKE_APP_ID).get_user()
    assert fake.requests == []


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("response", "message"),
    [
        (httpx2.Response(500), "HTTP 500"),
        (httpx2.Response(200, json=["not", "an", "object"]), "unexpected payload"),
    ],
)
async def test_unexpected_answers_raise_api_errors(response: httpx2.Response, message: str) -> None:
    async with client_answering(lambda request: response) as http:
        with pytest.raises(QobuzApiError, match=message):
            await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get_user()


@pytest.mark.anyio
async def test_network_errors_raise_api_errors_without_secrets() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("unreachable", request=request)

    async with client_answering(fail) as http:
        with pytest.raises(QobuzApiError) as error_info:
            await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get_user()
    assert FAKE_TOKEN not in str(error_info.value)


@pytest.mark.anyio
async def test_oauth_exchange_without_token_in_the_answer_fails() -> None:
    async with client_answering(lambda request: httpx2.Response(200, json={})) as http:
        with pytest.raises(QobuzApiError, match="no token"):
            await QobuzClient(http, FAKE_APP_ID).exchange_oauth_code("code", "key")
