class QobuzError(Exception):
    """Base class of the errors reported to the user. Messages never contain secrets."""


class WebPlayerError(QobuzError):
    """The Qobuz web player page or bundle could not be loaded."""


class AppIdExtractionError(QobuzError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Could not find the app_id in the Qobuz web player ({reason}). "
            "Set the QOBUZ_APP_ID environment variable to work around it."
        )


class PrivateKeyExtractionError(QobuzError):
    def __init__(self, reason: str) -> None:
        super().__init__(
            f"Could not find the OAuth private key in the Qobuz web player ({reason}). "
            "Run `qobuz-mcp login --token` to log in with a token copied from the web player."
        )


class LoginTimeoutError(QobuzError):
    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            f"No sign-in completed within {timeout_seconds:g} seconds. Run `qobuz-mcp login` again."
        )


class KeychainError(QobuzError):
    def __init__(self) -> None:
        super().__init__(
            "Could not access the macOS Keychain. Unlock it, or allow access when macOS asks, "
            "then try again."
        )


class AuthenticationError(QobuzError):
    """Not logged in, or Qobuz rejected the credentials."""


class InvalidAppIdError(QobuzError):
    """Qobuz rejected the app_id."""


class ForbiddenError(QobuzError):
    """Qobuz refused the operation, typically a write on a playlist the user does not own."""


class DuplicateTracksError(QobuzError):
    """Qobuz refused to add tracks already in the playlist, and added none."""


class NotFoundError(QobuzError):
    """Qobuz found no item for the requested IDs."""


class QobuzUnavailableError(QobuzError):
    """Qobuz rate limited the request, failed, or could not be reached."""


class QobuzApiError(QobuzError):
    """Qobuz answered with an unexpected status or payload."""
