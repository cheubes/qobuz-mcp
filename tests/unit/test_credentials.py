import keyring
import pytest

from qobuz_mcp.credentials import (
    KEYCHAIN_ACCOUNT,
    KEYCHAIN_SERVICE,
    Credentials,
    delete_credentials,
    load_credentials,
    save_credentials,
)
from tests.fakes import FAKE_APP_ID, FAKE_TOKEN, as_json

CREDENTIALS = Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN)


def test_credentials_round_trip_as_one_json_item() -> None:
    save_credentials(CREDENTIALS)
    assert as_json(keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)) == {
        "app_id": FAKE_APP_ID,
        "user_auth_token": FAKE_TOKEN,
    }
    assert load_credentials() == CREDENTIALS


def test_missing_or_unreadable_credentials_load_as_none() -> None:
    assert load_credentials() is None
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, "not json")
    assert load_credentials() is None
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, '{"app_id": "1"}')
    assert load_credentials() is None


def test_delete_credentials_reports_whether_there_were_any() -> None:
    save_credentials(CREDENTIALS)
    assert delete_credentials() is True
    assert delete_credentials() is False


def test_repr_never_shows_the_token() -> None:
    assert FAKE_TOKEN not in repr(CREDENTIALS)


def test_app_id_override_replaces_the_stored_app_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """AC-SETUP-06"""
    save_credentials(CREDENTIALS)
    monkeypatch.setenv("QOBUZ_APP_ID", "987654321")
    assert load_credentials() == Credentials(app_id="987654321", user_auth_token=FAKE_TOKEN)
    monkeypatch.setenv("QOBUZ_APP_ID", "")
    assert load_credentials() == CREDENTIALS
