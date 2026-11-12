import re
from collections.abc import Mapping, Sequence
from typing import Any

import httpx2

from qobuz_mcp.errors import (
    AuthenticationError,
    ForbiddenError,
    InvalidAppIdError,
    NotFoundError,
    QobuzApiError,
    QobuzError,
    QobuzUnavailableError,
)

API_BASE_URL = "https://www.qobuz.com/api.json/0.2/"
REQUEST_TIMEOUT_SECONDS = 15.0

type ParamValue = str | int | bool | Sequence[str | int] | None

_APP_ID_MESSAGE = re.compile(r"app[_ ]?id", re.IGNORECASE)


def encode_params(params: Mapping[str, ParamValue]) -> dict[str, str]:
    """Encode parameters as the web player does: comma-separated lists, `true`/`false`."""
    encoded: dict[str, str] = {}
    for name, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            encoded[name] = "true" if value else "false"
        elif isinstance(value, str | int):
            encoded[name] = str(value)
        else:
            encoded[name] = ",".join(str(item) for item in value)
    return encoded


def requested_ids(params: Mapping[str, str]) -> str:
    """Describe the requested IDs for error messages. No other parameter is ever included."""
    ids = [f"{name}={value}" for name, value in params.items() if name.endswith(("_id", "_ids"))]
    return ", ".join(ids) or "no ID"


class QobuzClient:
    """Calls to the Qobuz API. Error messages never contain request parameters or headers,
    except the requested IDs."""

    def __init__(
        self, http: httpx2.AsyncClient, app_id: str, user_auth_token: str | None = None
    ) -> None:
        self._http = http
        self._app_id = app_id
        self._user_auth_token = user_auth_token

    async def exchange_oauth_code(self, code: str, private_key: str) -> str:
        """Exchange the authorization code of the OAuth redirect for a user auth token."""
        try:
            payload = await self.get(
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
        return await self.get("user/get")

    async def get_album(self, album_id: str, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get("album/get", {"album_id": album_id, "limit": limit, "offset": offset})

    async def get_artist(self, artist_id: int, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "artist/get",
            {"artist_id": artist_id, "extra": "albums", "limit": limit, "offset": offset},
        )

    async def get_similar_artists(
        self, artist_id: int, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "artist/getSimilarArtists", {"artist_id": artist_id, "limit": limit, "offset": offset}
        )

    async def get_label(self, label_id: int, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "label/get",
            {"label_id": label_id, "extra": "albums", "limit": limit, "offset": offset},
        )

    async def list_genres(
        self, parent_genre_id: int | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "genre/list", {"parent_id": parent_genre_id, "limit": limit, "offset": offset}
        )

    async def list_featured_albums(
        self, category: str, genre_id: int | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "album/getFeatured",
            {"type": category, "genre_ids": genre_id, "limit": limit, "offset": offset},
        )

    async def list_featured_playlists(
        self, genre_id: int | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        # The API ignores `type`, but the web player always sends it.
        return await self.get(
            "playlist/getFeatured",
            {"type": "editor-picks", "genre_ids": genre_id, "limit": limit, "offset": offset},
        )

    async def list_favorites(self, kind: str, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "favorite/getUserFavorites", {"type": kind, "limit": limit, "offset": offset}
        )

    async def get_playlist(self, playlist_id: int, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "playlist/get",
            {"playlist_id": playlist_id, "extra": "tracks", "limit": limit, "offset": offset},
        )

    async def get_track(self, track_id: int) -> dict[str, Any]:
        return await self.get("track/get", {"track_id": track_id})

    async def search_catalog(
        self, query: str, kind: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "catalog/search", {"query": query, "type": kind, "limit": limit, "offset": offset}
        )

    async def get(
        self,
        endpoint: str,
        params: Mapping[str, ParamValue] | None = None,
        *,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        """Read endpoint: GET with query parameters."""
        return await self._request("GET", endpoint, encode_params(params or {}), authenticated)

    async def post(self, endpoint: str, params: Mapping[str, ParamValue]) -> dict[str, Any]:
        """Write endpoint: POST with a form-encoded body, as the web player does."""
        return await self._request("POST", endpoint, encode_params(params), authenticated=True)

    async def _request(
        self, method: str, endpoint: str, params: dict[str, str], authenticated: bool
    ) -> dict[str, Any]:
        headers = {"X-App-Id": self._app_id}
        if authenticated:
            if self._user_auth_token is None:
                raise AuthenticationError("Not logged in. Run `qobuz-mcp login`.")
            headers["X-User-Auth-Token"] = self._user_auth_token
        url = API_BASE_URL + endpoint
        try:
            if method == "GET":
                response = await self._http.get(url, params=params, headers=headers)
            else:
                response = await self._http.post(url, data=params, headers=headers)
        except httpx2.HTTPError as error:
            raise QobuzUnavailableError(
                f"Qobuz could not be reached ({type(error).__name__})."
            ) from error
        if response.status_code != 200:
            raise _error_for(response, endpoint, params)
        payload = _json_object(response)
        if payload is None:
            raise QobuzApiError(f"Qobuz answered {endpoint} with an unexpected payload.")
        return payload


def _json_object(response: httpx2.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None
    return payload if isinstance(payload, dict) else None


def _error_for(response: httpx2.Response, endpoint: str, params: dict[str, str]) -> QobuzError:
    status = response.status_code
    payload = _json_object(response) or {}
    message = payload.get("message")
    if status == 401:
        return AuthenticationError("Qobuz rejected the credentials. Run `qobuz-mcp login`.")
    if status == 400 and isinstance(message, str) and _APP_ID_MESSAGE.search(message):
        return InvalidAppIdError(
            "Qobuz rejected the app_id. Run `qobuz-mcp login` again, or set QOBUZ_APP_ID."
        )
    if status == 403:
        return ForbiddenError(f"Qobuz refused {endpoint} for {requested_ids(params)}.")
    if status == 404:
        return NotFoundError(f"Qobuz found nothing for {requested_ids(params)}.")
    if status == 429 or status >= 500:
        return QobuzUnavailableError(f"Qobuz is unavailable (HTTP {status}). Try again later.")
    return QobuzApiError(f"Qobuz answered {endpoint} with HTTP {status}.")
