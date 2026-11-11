import httpx2
import pytest

from qobuz_mcp.errors import AppIdExtractionError, PrivateKeyExtractionError, WebPlayerError
from qobuz_mcp.web_player import extract_app_id, extract_private_key, fetch_bundle
from tests.fakes import BUNDLE, FAKE_APP_ID, FAKE_PRIVATE_KEY, FakeQobuz


@pytest.mark.anyio
async def test_fetch_bundle_follows_the_login_page() -> None:
    fake = FakeQobuz()
    async with fake.client() as http:
        assert await fetch_bundle(http) == BUNDLE
    assert [request.url.path for request in fake.requests] == [
        "/login",
        "/resources/0.0.0-test/bundle.js",
    ]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "fake",
    [FakeQobuz(login_page="<html>no script</html>"), FakeQobuz(web_player_status=503)],
)
async def test_fetch_bundle_reports_an_unusable_web_player(fake: FakeQobuz) -> None:
    async with fake.client() as http:
        with pytest.raises(WebPlayerError):
            await fetch_bundle(http)


@pytest.mark.anyio
async def test_fetch_bundle_reports_network_errors() -> None:
    def fail(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ConnectError("unreachable", request=request)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(fail)) as http:
        with pytest.raises(WebPlayerError, match="ConnectError"):
            await fetch_bundle(http)


def test_extract_app_id_reads_the_production_configuration_only() -> None:
    assert extract_app_id(BUNDLE) == FAKE_APP_ID


def test_extract_private_key() -> None:
    assert extract_private_key(BUNDLE) == FAKE_PRIVATE_KEY


def test_missing_app_id_suggests_the_environment_override() -> None:
    with pytest.raises(AppIdExtractionError, match="QOBUZ_APP_ID"):
        extract_app_id("var nothing;")


def test_missing_private_key_suggests_token_login() -> None:
    with pytest.raises(PrivateKeyExtractionError, match="login --token"):
        extract_private_key("var nothing;")
