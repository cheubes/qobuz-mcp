import socket
import threading
import urllib.parse

import pytest

from qobuz_mcp import oauth
from qobuz_mcp.api import QobuzClient
from qobuz_mcp.errors import AuthenticationError, LoginTimeoutError
from qobuz_mcp.oauth import CallbackServer, run_browser_login
from tests.fakes import (
    FAKE_APP_ID,
    FAKE_CODE,
    FAKE_PRIVATE_KEY,
    FAKE_TOKEN,
    FakeBrowser,
    FakeQobuz,
    get_status,
)


def test_callback_server_accepts_only_the_first_valid_callback() -> None:
    """AC-SETUP-14"""
    server = CallbackServer()
    server.start()
    try:
        origin = server.callback_url.rsplit("/callback/", 1)[0]
        assert get_status(origin + "/favicon.ico") == 404
        assert get_status(origin + "/callback/wrong-nonce?code_autorisation=forged") == 404
        assert get_status(server.callback_url) == 404
        assert get_status(server.callback_url + "?code_autorisation=first") == 200
        assert get_status(server.callback_url + "?code_autorisation=second") == 404
        assert server.wait_for_code(1) == "first"
    finally:
        server.close()


def test_callback_server_listens_on_loopback_only_and_closes() -> None:
    """AC-SETUP-16"""
    server = CallbackServer()
    server.start()
    host, port = server.address
    assert host == "127.0.0.1"
    server.close()
    with pytest.raises(OSError), socket.create_connection((host, port), timeout=1):
        pass


def test_close_releases_a_pending_wait() -> None:
    """AC-SETUP-21"""
    server = CallbackServer()
    server.start()
    waiter = threading.Thread(target=server.wait_for_code, args=(oauth.LOGIN_TIMEOUT_SECONDS,))
    waiter.start()
    server.close()
    waiter.join(timeout=1)
    assert not waiter.is_alive()


def test_wait_for_code_returns_none_on_timeout() -> None:
    server = CallbackServer()
    server.start()
    try:
        assert server.wait_for_code(0.05) is None
    finally:
        server.close()


@pytest.mark.anyio
async def test_browser_login_returns_the_token_of_the_redirect() -> None:
    fake, browser = FakeQobuz(), FakeBrowser()
    output: list[str] = []
    async with fake.client() as http:
        token = await run_browser_login(
            QobuzClient(http, FAKE_APP_ID),
            FAKE_APP_ID,
            FAKE_PRIVATE_KEY,
            open_browser=browser.open,
            output=output.append,
        )
    assert token == FAKE_TOKEN
    sign_in = urllib.parse.urlsplit(browser.opened_urls[0])
    assert f"{sign_in.scheme}://{sign_in.netloc}{sign_in.path}" == oauth.SIGN_IN_URL
    query = urllib.parse.parse_qs(sign_in.query)
    assert query["ext_app_id"] == [FAKE_APP_ID]
    assert query["redirect_url"][0].startswith("http://127.0.0.1:")
    assert browser.statuses == {"/favicon.ico": 404, "callback": 200}
    assert browser.opened_urls[0] in output[0]
    assert all(FAKE_CODE not in line and FAKE_TOKEN not in line for line in output)


@pytest.mark.anyio
async def test_browser_login_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oauth, "LOGIN_TIMEOUT_SECONDS", 0.2)
    async with FakeQobuz().client() as http:
        with pytest.raises(LoginTimeoutError):
            await run_browser_login(
                QobuzClient(http, FAKE_APP_ID),
                FAKE_APP_ID,
                FAKE_PRIVATE_KEY,
                open_browser=FakeBrowser(code=None).open,
                output=lambda line: None,
            )


@pytest.mark.anyio
async def test_browser_login_reports_a_rejected_code() -> None:
    async with FakeQobuz(oauth_status=401).client() as http:
        with pytest.raises(AuthenticationError, match="rejected the sign-in"):
            await run_browser_login(
                QobuzClient(http, FAKE_APP_ID),
                FAKE_APP_ID,
                FAKE_PRIVATE_KEY,
                open_browser=FakeBrowser().open,
                output=lambda line: None,
            )
