import json
from dataclasses import dataclass, field

import keyring
from keyring.errors import PasswordDeleteError

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
    keyring.set_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT, value)


def load_credentials() -> Credentials | None:
    """Return the stored credentials, or None when missing or unreadable."""
    raw = keyring.get_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    if raw is None:
        return None
    try:
        value = json.loads(raw)
        return Credentials(app_id=value["app_id"], user_auth_token=value["user_auth_token"])
    except ValueError, KeyError, TypeError:
        return None


def delete_credentials() -> bool:
    """Delete the stored credentials. Return False when there were none."""
    try:
        keyring.delete_password(KEYCHAIN_SERVICE, KEYCHAIN_ACCOUNT)
    except PasswordDeleteError:
        return False
    return True
