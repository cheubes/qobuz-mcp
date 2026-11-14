import re
from collections.abc import Mapping, Sequence
from typing import Any

import httpx2

from qobuz_mcp.errors import (
    AuthenticationError,
    DuplicateTracksError,
    ForbiddenError,
    InvalidAppIdError,
    NotFoundError,
    QobuzApiError,
    QobuzError,
    QobuzUnavailableError,
)

API_BASE_URL = "https://www.qobuz.com/api.json/0.2/"
REQUEST_TIMEOUT_SECONDS = 15.0

LABEL_SECTION_ENDPOINTS = {
    "top_artists": "label/getTopArtists",
    "upcoming_releases": "label/getNextReleases",
    "playlists": "label/getPlaylists",
    "awarded_releases": "label/getAwardedReleases",
}

# Featured album categories served by the current web player endpoints (ADR-0035). The other
# categories stay on album/getFeatured.
DISCOVER_ALBUM_ENDPOINTS = {
    "new-releases": "discover/newReleases",
    "qobuzissims": "discover/qobuzissims",
    "ideal-discography": "discover/idealDiscography",
    "most-streamed": "discover/mostStreamed",
    "press-awards": "discover/pressAward",
    "album-of-the-week": "discover/albumOfTheWeek",
}

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

    async def get_artist(self, artist_id: int) -> dict[str, Any]:
        return await self.get("artist/page", {"artist_id": artist_id, "sort": "relevant"})

    async def list_artist_releases(
        self, artist_id: int, release_type: str | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "artist/getReleasesList",
            {
                "artist_id": artist_id,
                "release_type": release_type,
                "sort": "release_date",
                "limit": limit,
                "offset": offset,
            },
        )

    async def get_similar_artists(
        self, artist_id: int, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "artist/getSimilarArtists", {"artist_id": artist_id, "limit": limit, "offset": offset}
        )

    async def get_label(self, label_id: int) -> dict[str, Any]:
        return await self.get("label/page", {"label_id": label_id})

    async def list_label_albums(self, label_id: int, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "label/getAlbums", {"label_id": label_id, "limit": limit, "offset": offset}
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
        if category in DISCOVER_ALBUM_ENDPOINTS:
            return await self.get(
                DISCOVER_ALBUM_ENDPOINTS[category],
                {"genre_ids": genre_id, "limit": limit, "offset": offset},
            )
        return await self.get(
            "album/getFeatured",
            {"type": category, "genre_ids": genre_id, "limit": limit, "offset": offset},
        )

    async def list_featured_playlists(
        self, genre_id: int | None, tag: str | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "discover/playlists",
            {"genre_ids": genre_id, "tags": tag, "limit": limit, "offset": offset},
        )

    async def list_favorites(self, kind: str, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "favorite/getUserFavorites", {"type": kind, "limit": limit, "offset": offset}
        )

    async def list_new_releases_from_favorites(
        self, source: str, genre_id: int | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "favorite/getNewReleases",
            {"type": source, "genre_ids": genre_id, "limit": limit, "offset": offset},
        )

    async def get_favorite_ids(self) -> dict[str, Any]:
        return await self.get("favorite/getUserFavoriteIds")

    async def get_purchase_ids(self) -> dict[str, Any]:
        return await self.get("purchase/getUserPurchasesIds")

    async def list_user_playlists(
        self, owner_filter: str | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "playlist/getUserPlaylists",
            {"filter": owner_filter, "limit": limit, "offset": offset},
        )

    async def list_purchases(self, kind: str, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get(
            "purchase/getUserPurchases", {"type": kind, "limit": limit, "offset": offset}
        )

    async def add_favorites(
        self, album_ids: list[str], artist_ids: list[int], track_ids: list[int]
    ) -> dict[str, Any]:
        return await self.post(
            "favorite/create",
            {"album_ids": album_ids, "artist_ids": artist_ids, "track_ids": track_ids},
        )

    async def remove_favorites(
        self, album_ids: list[str], artist_ids: list[int], track_ids: list[int]
    ) -> dict[str, Any]:
        return await self.post(
            "favorite/delete",
            {"album_ids": album_ids, "artist_ids": artist_ids, "track_ids": track_ids},
        )

    async def create_playlist(
        self, name: str, description: str, *, is_public: bool, is_collaborative: bool
    ) -> dict[str, Any]:
        return await self.post(
            "playlist/create",
            {
                "name": name,
                "description": description,
                "is_public": is_public,
                "is_collaborative": is_collaborative,
            },
        )

    async def update_playlist(
        self,
        playlist_id: int,
        *,
        name: str | None,
        description: str | None,
        is_public: bool | None,
        is_collaborative: bool | None,
    ) -> dict[str, Any]:
        return await self.post(
            "playlist/update",
            {
                "playlist_id": playlist_id,
                "name": name,
                "description": description,
                "is_public": is_public,
                "is_collaborative": is_collaborative,
            },
        )

    async def add_tracks_to_playlist(
        self, playlist_id: int, track_ids: list[int]
    ) -> dict[str, Any]:
        return await self.post(
            "playlist/addTracks",
            {"playlist_id": playlist_id, "track_ids": track_ids, "no_duplicate": True},
        )

    async def remove_tracks_from_playlist(
        self, playlist_id: int, playlist_track_ids: list[int]
    ) -> dict[str, Any]:
        return await self.post(
            "playlist/deleteTracks",
            {"playlist_id": playlist_id, "playlist_track_ids": playlist_track_ids},
        )

    async def move_playlist_tracks(
        self, playlist_id: int, playlist_track_ids: list[int], insert_before: int
    ) -> dict[str, Any]:
        return await self.post(
            "playlist/updateTracksPosition",
            {
                "playlist_id": playlist_id,
                "playlist_track_ids": playlist_track_ids,
                "insert_before": insert_before,
            },
        )

    async def delete_playlist(self, playlist_id: int) -> dict[str, Any]:
        return await self.post("playlist/delete", {"playlist_id": playlist_id})

    async def follow_playlist(self, playlist_id: int) -> dict[str, Any]:
        return await self.post("playlist/subscribe", {"playlist_id": playlist_id})

    async def unfollow_playlist(self, playlist_id: int) -> dict[str, Any]:
        return await self.post("playlist/unsubscribe", {"playlist_id": playlist_id})

    async def list_similar_albums(self, album_id: str) -> dict[str, Any]:
        return await self.get("album/suggest", {"album_id": album_id})

    async def get_radio(self, seed_type: str, seed_id: str) -> dict[str, Any]:
        return await self.get(f"radio/{seed_type}", {f"{seed_type}_id": seed_id})

    async def suggest_tracks(self, seeds: list[dict[str, int]], *, limit: int) -> dict[str, Any]:
        return await self.post_json(
            "dynamic/suggest",
            {
                "limit": limit,
                "listened_tracks_ids": [seed["track_id"] for seed in seeds],
                "track_to_analysed": seeds,
            },
        )

    async def list_artist_playlists(
        self, artist_id: int, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "artist/playlists", {"artist_id": artist_id, "limit": limit, "offset": offset}
        )

    async def list_label_items(
        self, label_id: int, section: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            LABEL_SECTION_ENDPOINTS[section],
            {"label_id": label_id, "limit": limit, "offset": offset},
        )

    async def list_awards(self, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get("award/explore", {"limit": limit, "offset": offset})

    async def get_award(self, award_id: int) -> dict[str, Any]:
        return await self.get("award/page", {"award_id": award_id})

    async def list_award_albums(
        self, award_id: int, genre_id: int | None, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            "award/getAlbums",
            {"award_id": award_id, "genre_ids": genre_id, "limit": limit, "offset": offset},
        )

    async def search_stories(self, query: str, *, limit: int, offset: int) -> dict[str, Any]:
        return await self.get("story/search", {"query": query, "limit": limit, "offset": offset})

    async def list_related_stories(
        self, entity_type: str, entity_id: str, *, limit: int, offset: int
    ) -> dict[str, Any]:
        return await self.get(
            f"{entity_type}/story",
            {f"{entity_type}_id": entity_id, "limit": limit, "offset": offset},
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

    async def post_json(self, endpoint: str, body: dict[str, Any]) -> dict[str, Any]:
        """POST with a JSON body, as the web player sends `dynamic/suggest`, a read."""
        return await self._request("POST", endpoint, {}, authenticated=True, json_body=body)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, str],
        authenticated: bool,
        json_body: dict[str, Any] | None = None,
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
            elif json_body is not None:
                response = await self._http.post(url, json=json_body, headers=headers)
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
        if "playlist_id" in params:
            return ForbiddenError(
                f"Qobuz refused {endpoint} for playlist_id={params['playlist_id']}: "
                "the playlist is not owned by the user."
            )
        return ForbiddenError(f"Qobuz refused {endpoint} for {requested_ids(params)}.")
    if status == 409 and endpoint == "playlist/addTracks":
        return DuplicateTracksError(
            f"Some of track_ids={params['track_ids']} are already in "
            f"playlist_id={params['playlist_id']}: nothing was added. "
            "Add only the tracks not yet in the playlist."
        )
    if status == 404:
        return NotFoundError(f"Qobuz found nothing for {requested_ids(params)}.")
    if status == 429 or status >= 500:
        return QobuzUnavailableError(f"Qobuz is unavailable (HTTP {status}). Try again later.")
    return QobuzApiError(f"Qobuz answered {endpoint} with HTTP {status}.")
