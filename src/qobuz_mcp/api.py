from typing import Any

import httpx2

from qobuz_mcp.errors import AuthenticationError, QobuzApiError, QobuzError

API_BASE_URL = "https://www.qobuz.com/api.json/0.2/"
REQUEST_TIMEOUT_SECONDS = 15.0


class QobuzClient:
    """Calls to the Qobuz API. Error messages never contain request parameters or headers."""

    def __init__(
        self, http: httpx2.AsyncClient, app_id: str, user_auth_token: str | None = None
    ) -> None:
        self._http = http
        self._app_id = app_id
        self._user_auth_token = user_auth_token

    async def exchange_oauth_code(self, code: str, private_key: str) -> str:
        """Exchange the authorization code of the OAuth redirect for a user auth token."""
        try:
            payload = await self._get(
                "oauth/callback", {"code": code, "private_key": private_key}, authenticated=False
            )
        except QobuzError as error:
            raise AuthenticationError(
                "Qobuz rejected the sign-in. Run `qobuz-mcp login` again."
            ) from error
        token = payload.get("token")
        if not isinstance(token, str) or not token:
            raise QobuzApiError("Qobuz returned no token after the sign-in.")
        return token

    async def get_user(self) -> dict[str, Any]:
        return await self._get("user/get", {}, authenticated=True)

    async def _get(
        self, endpoint: str, params: dict[str, str], *, authenticated: bool
    ) -> dict[str, Any]:
        headers = {"X-App-Id": self._app_id}
        if authenticated:
            if self._user_auth_token is None:
                raise AuthenticationError("Not logged in. Run `qobuz-mcp login`.")
            headers["X-User-Auth-Token"] = self._user_auth_token
        try:
            response = await self._http.get(API_BASE_URL + endpoint, params=params, headers=headers)
        except httpx2.HTTPError as error:
            raise QobuzApiError(f"Qobuz is unreachable ({type(error).__name__}).") from error
        if response.status_code == 401:
            raise AuthenticationError("Qobuz rejected the credentials.")
        if response.status_code != 200:
            raise QobuzApiError(f"Qobuz answered {endpoint} with HTTP {response.status_code}.")
        payload = response.json()
        if not isinstance(payload, dict):
            raise QobuzApiError(f"Qobuz answered {endpoint} with an unexpected payload.")
        return payload
