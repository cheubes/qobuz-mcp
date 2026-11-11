import re

import httpx2

from qobuz_mcp.errors import AppIdExtractionError, PrivateKeyExtractionError, WebPlayerError

WEB_PLAYER_URL = "https://play.qobuz.com"

_BUNDLE_PATH = re.compile(r'src="(/resources/[^"]+/bundle\.js)"')
_APP_ID = re.compile(r'production:\{api:\{appId:"(\d{9})"')
_PRIVATE_KEY = re.compile(r'authenticate\(\{privateKey:"([^"]+)"')


async def fetch_bundle(http: httpx2.AsyncClient) -> str:
    """Download the web player bundle, which holds the app_id and the OAuth private key."""
    try:
        page = await http.get(f"{WEB_PLAYER_URL}/login")
        page.raise_for_status()
        bundle_path = _BUNDLE_PATH.search(page.text)
        if bundle_path is None:
            raise WebPlayerError("the login page references no bundle")
        bundle = await http.get(WEB_PLAYER_URL + bundle_path.group(1))
        bundle.raise_for_status()
    except httpx2.HTTPError as error:
        raise WebPlayerError(f"web player unavailable: {type(error).__name__}") from error
    return bundle.text


def extract_app_id(bundle: str) -> str:
    match = _APP_ID.search(bundle)
    if match is None:
        raise AppIdExtractionError("pattern not found in the bundle")
    return match.group(1)


def extract_private_key(bundle: str) -> str:
    match = _PRIVATE_KEY.search(bundle)
    if match is None:
        raise PrivateKeyExtractionError("pattern not found in the bundle")
    return match.group(1)
