import json
import os
from dataclasses import dataclass, field

import keyring
from keyring.errors import KeyringError

from qobuz_mcp.errors import KeychainError

KEYCHAIN_SERVICE = "qobuz-mcp"
KEYCHAIN_ACCOUNT = "default"


@dataclass(frozen=True)
class Credentials:
    app_id: str
    user_auth_token: str = field(repr=False)


def save_credentials(credentials: Credentials) -> None:
    value = json.dumps(
        {"app_id": credentials.app_id, "user_auth_token": credentials.user_auth_token}
    )
    try:
        keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, value)
    except KeyringError as error:
        raise KeychainError() from error


APP_ID_OVERRIDE_VARIABLE = "QOBUZ_APP_ID"


def load_credentials() -> Credentials | None:
    """Return the stored credentials, or None when missing or unreadable.

    `QOBUZ_APP_ID`, when set, replaces the stored app_id.
    """
    raw = _read_item()
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        app_id = os.environ.get(APP_ID_OVERRIDE_VARIABLE) or value["app_id"]
        return Credentials(app_id=app_id, user_auth_token=value["user_auth_token"])
    except ValueError, KeyError, TypeError:
        return None


def delete_credentials() -> bool:
    """Delete the stored credentials. Return False when there were none."""
    # The macOS backend raises the same PasswordDeleteError for a missing item and for a
    # denied access, so the item is looked up first.
    if _read_item() is None:
        return False
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except KeyringError as error:
        raise KeychainError() from error
    return True


def _read_item() -> str | None:
    try:
        return keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except KeyringError as error:
        raise KeychainError() from error
