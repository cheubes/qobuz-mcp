import asyncio
import secrets
import threading
import urllib.parse
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from qobuz_mcp.api import QobuzClient
from qobuz_mcp.errors import LoginTimeoutError

SIGN_IN_URL = "https://www.qobuz.com/signin/oauth"
LOGIN_TIMEOUT_SECONDS = 300.0
CALLBACK_HOST = "127.0.0.1"

_SIGNED_IN_PAGE = (
    b"<!doctype html><meta charset=utf-8><title>qobuz-mcp</title>"
    b"<p>Signed in to Qobuz. You can close this tab and go back to the terminal.</p>"
)


class CallbackServer:
    """Local HTTP server receiving the OAuth redirect, on 127.0.0.1 only.

    Only `GET /callback/<nonce>?code_autorisation=...` is accepted, and only once: the random
    nonce replaces the `state` parameter the Qobuz flow lacks.
    """

    def __init__(self) -> None:
        self._path = f"/callback/{secrets.token_urlsafe(16)}"
        self._code: str | None = None
        self._received = threading.Event()
        self._lock = threading.Lock()
        self._httpd = ThreadingHTTPServer((CALLBACK_HOST, 0), self._handler_class())
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    @property
    def callback_url(self) -> str:
        return f"http://{CALLBACK_HOST}:{self._httpd.server_port}{self._path}"

    @property
    def address(self) -> tuple[str, int]:
        host, port = self._httpd.server_address[:2]
        return str(host), int(port)

    def start(self) -> None:
        self._thread.start()

    def wait_for_code(self, timeout_seconds: float) -> str | None:
        self._received.wait(timeout_seconds)
        return self._code

    def close(self) -> None:
        if self._thread.is_alive():
            self._httpd.shutdown()
            self._thread.join()
        self._httpd.server_close()

    def _accept(self, path: str, query: str) -> bool:
        codes = urllib.parse.parse_qs(query).get("code_autorisation")
        if path != self._path or not codes:
            return False
        with self._lock:
            if self._code is not None:
                return False
            self._code = codes[0]
        self._received.set()
        return True

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        callback_server = self

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                url = urllib.parse.urlsplit(self.path)
                if not callback_server._accept(url.path, url.query):
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(_SIGNED_IN_PAGE)))
                self.end_headers()
                self.wfile.write(_SIGNED_IN_PAGE)

            def log_message(self, format: str, *args: object) -> None:
                # The default logs the request line, which carries the authorization code.
                pass

        return CallbackHandler


async def run_browser_login(
    qobuz: QobuzClient,
    app_id: str,
    private_key: str,
    *,
    open_browser: Callable[[str], object],
    output: Callable[[str], None],
) -> str:
    """Run the Qobuz OAuth browser flow and return the user auth token."""
    server = CallbackServer()
    server.start()
    try:
        query = urllib.parse.urlencode({"ext_app_id": app_id, "redirect_url": server.callback_url})
        sign_in_url = f"{SIGN_IN_URL}?{query}"
        output(
            "Opening the Qobuz sign-in page in your browser. If it does not open, visit:\n"
            f"{sign_in_url}"
        )
        open_browser(sign_in_url)
        code = await asyncio.to_thread(server.wait_for_code, LOGIN_TIMEOUT_SECONDS)
    finally:
        server.close()
    if code is None:
        raise LoginTimeoutError(LOGIN_TIMEOUT_SECONDS)
    return await qobuz.exchange_oauth_code(code, private_key)
