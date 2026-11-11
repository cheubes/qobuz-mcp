import argparse
import asyncio
import getpass
import os
import sys
import webbrowser
from collections.abc import Sequence

import httpx2

from qobuz_mcp.api import REQUEST_TIMEOUT_SECONDS, QobuzClient
from qobuz_mcp.credentials import Credentials, delete_credentials, save_credentials
from qobuz_mcp.errors import (
    AppIdExtractionError,
    AuthenticationError,
    PrivateKeyExtractionError,
    QobuzError,
    WebPlayerError,
)
from qobuz_mcp.oauth import run_browser_login
from qobuz_mcp.web_player import extract_app_id, extract_private_key, fetch_bundle


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qobuz-mcp", description="Local MCP server for Qobuz.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Start the MCP server on stdio.")
    login = commands.add_parser("login", help="Sign in to Qobuz and store the credentials.")
    login.add_argument(
        "--token",
        action="store_true",
        help="Paste a token copied from the web player instead of signing in in the browser.",
    )
    commands.add_parser("logout", help="Delete the stored credentials.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    if arguments.command == "serve":
        # stdout is reserved for the MCP protocol.
        print("qobuz-mcp serve: not implemented yet", file=sys.stderr)
        return 1
    try:
        if arguments.command == "login":
            asyncio.run(_login(with_token=arguments.token))
        else:
            _logout()
    except QobuzError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


def _http_client() -> httpx2.AsyncClient:
    return httpx2.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)


async def _login(*, with_token: bool) -> None:
    app_id_override = os.environ.get("QOBUZ_APP_ID")
    async with _http_client() as http:
        bundle = ""
        if app_id_override is None or not with_token:
            try:
                bundle = await fetch_bundle(http)
            except WebPlayerError as error:
                if app_id_override is None:
                    raise AppIdExtractionError(str(error)) from error
                raise PrivateKeyExtractionError(str(error)) from error
        app_id = app_id_override or extract_app_id(bundle)

        if with_token:
            user_auth_token = getpass.getpass("Qobuz token: ").strip()
        else:
            private_key = extract_private_key(bundle)
            user_auth_token = await run_browser_login(
                QobuzClient(http, app_id),
                app_id,
                private_key,
                open_browser=webbrowser.open,
                output=print,
            )

        try:
            user = await QobuzClient(http, app_id, user_auth_token).get_user()
        except AuthenticationError as error:
            raise AuthenticationError("Qobuz rejected the token. Nothing was stored.") from error

    save_credentials(Credentials(app_id=app_id, user_auth_token=user_auth_token))
    display_name = user.get("display_name") or "your Qobuz account"
    print(f"Logged in as {display_name}. Credentials stored in the macOS Keychain.")


def _logout() -> None:
    if delete_credentials():
        print("Logged out: credentials removed from the macOS Keychain.")
    else:
        print("Not logged in: no credentials to remove.")
