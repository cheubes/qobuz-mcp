import httpx2
import pytest

from qobuz_mcp.web_player import extract_app_id, extract_private_key, fetch_bundle

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_app_id_extraction_from_the_real_web_player(live_http: httpx2.AsyncClient) -> None:
    """AC-LIVE-01"""
    app_id = extract_app_id(await fetch_bundle(live_http))
    assert app_id.isdigit()


async def test_private_key_extraction_from_the_real_web_player(
    live_http: httpx2.AsyncClient,
) -> None:
    """AC-LIVE-06"""
    assert extract_private_key(await fetch_bundle(live_http))
