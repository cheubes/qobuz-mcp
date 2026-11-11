from collections.abc import Callable

import httpx2
import pytest

from qobuz_mcp.api import API_BASE_URL, QobuzClient, encode_params
from qobuz_mcp.credentials import Credentials, load_credentials, save_credentials
from qobuz_mcp.errors import (
    AuthenticationError,
    ForbiddenError,
    InvalidAppIdError,
    NotFoundError,
    QobuzApiError,
    QobuzError,
    QobuzUnavailableError,
)
from qobuz_mcp.web_player import fetch_bundle
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, FakeQobuz

Handler = Callable[[httpx2.Request], httpx2.Response]


def client_answering(handler: Handler) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(transport=httpx2.MockTransport(handler))


def answer(status: int, message: str = "") -> Handler:
    return lambda request: httpx2.Response(
        status, json={"status": "error", "code": status, "message": message}
    )


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
async def test_reads_send_encoded_query_parameters() -> None:
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={})

    async with client_answering(record) as http:
        await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get(
            "album/getFeatured", {"type": "new-releases", "genre_ids": [1, 2], "offset": None}
        )
    request = requests[0]
    assert request.method == "GET"
    assert dict(request.url.params) == {"type": "new-releases", "genre_ids": "1,2"}


@pytest.mark.anyio
async def test_writes_send_a_form_encoded_body() -> None:
    requests: list[httpx2.Request] = []

    def record(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={"status": "success"})

    async with client_answering(record) as http:
        payload = await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).post(
            "playlist/addTracks", {"playlist_id": 7, "track_ids": [1, 2, 3], "no_duplicate": True}
        )
    assert payload == {"status": "success"}
    request = requests[0]
    assert request.method == "POST"
    assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
    assert request.content == b"playlist_id=7&track_ids=1%2C2%2C3&no_duplicate=true"
    assert request.url.query == b""


def test_encode_params() -> None:
    assert encode_params(
        {"text": "a", "number": 3, "yes": True, "no": False, "ids": ["x", 4], "absent": None}
    ) == {"text": "a", "number": "3", "yes": "true", "no": "false", "ids": "x,4"}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("handler", "error_type", "message"),
    [
        (answer(401), AuthenticationError, "qobuz-mcp login"),
        (answer(400, "Invalid or missing app_id parameter."), InvalidAppIdError, "QOBUZ_APP_ID"),
        (answer(400, "Invalid argument: type"), QobuzApiError, "HTTP 400"),
        (answer(403), ForbiddenError, "playlist_id=7"),
        (answer(404), NotFoundError, "playlist_id=7"),
        (answer(429), QobuzUnavailableError, "Try again later"),
        (answer(503), QobuzUnavailableError, "Try again later"),
        (lambda request: httpx2.Response(502, text="<html>"), QobuzUnavailableError, "HTTP 502"),
        (answer(418), QobuzApiError, "HTTP 418"),
        (lambda request: httpx2.Response(200, json=["list"]), QobuzApiError, "payload"),
        (lambda request: httpx2.Response(200, text="not json"), QobuzApiError, "payload"),
    ],
)
async def test_error_mapping(handler: Handler, error_type: type[QobuzError], message: str) -> None:
    async with client_answering(handler) as http:
        with pytest.raises(error_type, match=message) as error_info:
            await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get(
                "playlist/get", {"playlist_id": 7, "extra": "tracks"}
            )
    assert type(error_info.value) is error_type
    assert FAKE_TOKEN not in str(error_info.value)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "exception", [httpx2.ConnectError("unreachable"), httpx2.ReadTimeout("too slow")]
)
async def test_network_errors_mean_qobuz_is_unavailable(exception: httpx2.HTTPError) -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise exception

    async with client_answering(fail) as http:
        with pytest.raises(QobuzUnavailableError) as error_info:
            await QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN).get_user()
    assert FAKE_TOKEN not in str(error_info.value)


@pytest.mark.anyio
async def test_error_messages_only_show_requested_ids() -> None:
    async with client_answering(answer(404)) as http:
        with pytest.raises(NotFoundError) as error_info:
            await QobuzClient(http, FAKE_APP_ID).get(
                "oauth/callback",
                {"code": "secret-code", "private_key": "secret-key"},
                authenticated=False,
            )
    assert "secret" not in str(error_info.value)


@pytest.mark.anyio
async def test_oauth_exchange_without_token_in_the_answer_fails() -> None:
    async with client_answering(lambda request: httpx2.Response(200, json={})) as http:
        with pytest.raises(QobuzApiError, match="no token"):
            await QobuzClient(http, FAKE_APP_ID).exchange_oauth_code("code", "key")


@pytest.mark.anyio
async def test_app_id_override_applies_to_api_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-SETUP-06"""
    save_credentials(Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN))
    monkeypatch.setenv("QOBUZ_APP_ID", "987654321")
    credentials = load_credentials()
    assert credentials is not None
    fake = FakeQobuz()
    async with fake.client() as http:
        await QobuzClient(http, credentials.app_id, credentials.user_auth_token).get_user()
    assert fake.requests[0].headers["X-App-Id"] == "987654321"


@pytest.mark.anyio
async def test_requests_only_go_to_qobuz_hosts() -> None:
    """AC-BEH-13"""
    fake = FakeQobuz()

    def accept_everything(request: httpx2.Request) -> httpx2.Response:
        response = fake.handle(request)
        return response if response.status_code != 404 else httpx2.Response(200, json={})

    async with client_answering(accept_everything) as http:
        await fetch_bundle(http)
        client = QobuzClient(http, FAKE_APP_ID, FAKE_TOKEN)
        await client.get_user()
        await client.get("album/get", {"album_id": "abc"})
        await client.post("favorite/create", {"album_ids": ["abc"]})
    assert {request.url.host for request in fake.requests} == {"play.qobuz.com", "www.qobuz.com"}
    assert all(request.url.scheme == "https" for request in fake.requests)
