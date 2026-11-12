from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.models import (
    AlbumSummary,
    ArtistSummary,
    Favorite,
    Page,
    PlaylistSummary,
    TrackSummary,
    album_summary,
    artist_summary,
    favorited_at,
    page_fields,
    playlist_summary,
    track_summary,
)
from qobuz_mcp.tools.common import DEFAULT_LIMIT, Limit, Offset, qobuz

FavoriteType = Literal["albums", "artists", "tracks"]
PlaylistFilter = Literal["owned", "followed"]
PurchaseType = Literal["albums", "tracks"]

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
