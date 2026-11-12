from typing import Annotated, Literal

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from qobuz_mcp.models import (
    AlbumSummary,
    ArtistSummary,
    Favorite,
    Page,
    PlaylistSummary,
    TrackSummary,
    WriteResult,
    album_summary,
    artist_summary,
    favorited_at,
    page_fields,
    playlist_summary,
    track_summary,
    write_result,
)
from qobuz_mcp.tools.common import DEFAULT_LIMIT, Limit, Offset, qobuz

FavoriteType = Literal["albums", "artists", "tracks"]
PlaylistFilter = Literal["owned", "followed"]
PurchaseType = Literal["albums", "tracks"]

AlbumIds = Annotated[list[str], Field(description="Qobuz album IDs (strings).")]
ArtistIds = Annotated[list[int], Field(description="Qobuz artist IDs (integers).")]
TrackIds = Annotated[list[int], Field(description="Qobuz track IDs (integers).")]

_QOBUZ_PLAYLIST_FILTERS: dict[PlaylistFilter, str] = {"owned": "owner", "followed": "subscriber"}


async def list_favorites(
    ctx: Context,
    type: Annotated[FavoriteType, Field(description="Kind of favorites to list.")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[Favorite[AlbumSummary]] | Page[Favorite[ArtistSummary]] | Page[Favorite[TrackSummary]]:
    """List the user's favorite albums, artists or tracks, newest first.

    Each item comes with `favorited_at`, the date it was added to the favorites.
    """
    payload = await qobuz(ctx).list_favorites(type, limit=limit, offset=offset)
    group = payload.get(type)
    match type:
        case "albums":
            return Page[Favorite[AlbumSummary]](
                **page_fields(
                    group,
                    lambda raw: Favorite[AlbumSummary](
                        item=album_summary(raw), favorited_at=favorited_at(raw)
                    ),
                    limit=limit,
                    offset=offset,
                )
            )
        case "artists":
            return Page[Favorite[ArtistSummary]](
                **page_fields(
                    group,
                    lambda raw: Favorite[ArtistSummary](
                        item=artist_summary(raw), favorited_at=favorited_at(raw)
                    ),
                    limit=limit,
                    offset=offset,
                )
            )
        case "tracks":
            return Page[Favorite[TrackSummary]](
                **page_fields(
                    group,
                    lambda raw: Favorite[TrackSummary](
                        item=track_summary(raw), favorited_at=favorited_at(raw)
                    ),
                    limit=limit,
                    offset=offset,
                )
            )


async def list_my_playlists(
    ctx: Context,
    filter: Annotated[
        PlaylistFilter | None,
        Field(
            description="Only playlists the user owns, or only those they follow. Omit for both."
        ),
    ] = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[PlaylistSummary]:
    """List the playlists the user owns or follows.

    Only playlists the user owns can be changed by the write tools.
    """
    owner_filter = _QOBUZ_PLAYLIST_FILTERS[filter] if filter else None
    payload = await qobuz(ctx).list_user_playlists(owner_filter, limit=limit, offset=offset)
    return Page[PlaylistSummary](
        **page_fields(payload.get("playlists"), playlist_summary, limit=limit, offset=offset)
    )


async def list_purchases(
    ctx: Context,
    type: Annotated[PurchaseType, Field(description="Kind of purchases to list.")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[AlbumSummary] | Page[TrackSummary]:
    """List the albums or tracks the user has purchased on Qobuz."""
    payload = await qobuz(ctx).list_purchases(type, limit=limit, offset=offset)
    group = payload.get(type)
    match type:
        case "albums":
            return Page[AlbumSummary](
                **page_fields(group, album_summary, limit=limit, offset=offset)
            )
        case "tracks":
            return Page[TrackSummary](
                **page_fields(group, track_summary, limit=limit, offset=offset)
            )


def _require_ids(album_ids: list[str], artist_ids: list[int], track_ids: list[int]) -> None:
    if not (album_ids or artist_ids or track_ids):
        raise ToolError("Give at least one album, artist or track ID.")


async def add_favorites(
    ctx: Context,
    album_ids: AlbumIds | None = None,
    artist_ids: ArtistIds | None = None,
    track_ids: TrackIds | None = None,
) -> WriteResult:
    """Add albums, artists and/or tracks to the user's favorites, in one call."""
    albums, artists, tracks = album_ids or [], artist_ids or [], track_ids or []
    _require_ids(albums, artists, tracks)
    return write_result(await qobuz(ctx).add_favorites(albums, artists, tracks))


async def remove_favorites(
    ctx: Context,
    album_ids: AlbumIds | None = None,
    artist_ids: ArtistIds | None = None,
    track_ids: TrackIds | None = None,
) -> WriteResult:
    """Remove albums, artists and/or tracks from the user's favorites, in one call."""
    albums, artists, tracks = album_ids or [], artist_ids or [], track_ids or []
    _require_ids(albums, artists, tracks)
    return write_result(await qobuz(ctx).remove_favorites(albums, artists, tracks))
