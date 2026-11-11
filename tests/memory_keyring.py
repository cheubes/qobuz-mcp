from keyring.backend import KeyringBackend
from keyring.errors import PasswordDeleteError


class MemoryKeyring(KeyringBackend):
    """Keyring backend kept in memory, so tests never touch the real Keychain."""

    # keyring reads the priority when it loads a backend from PYTHON_KEYRING_BACKEND.
    priority = 1.0

    def __init__(self) -> None:
        super().__init__()  # type: ignore[no-untyped-call]  # keyring's base __init__ is untyped
        self._passwords: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._passwords.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._passwords[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self._passwords[(service, username)]
        except KeyError:
            raise PasswordDeleteError(f"{service}/{username} not found") from None
