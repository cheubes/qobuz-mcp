from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.models import (
    AlbumSummary,
    ArtistSummary,
    Favorite,
    Page,
    TrackSummary,
    album_summary,
    artist_summary,
    favorited_at,
    page_fields,
    track_summary,
)
from qobuz_mcp.tools.common import DEFAULT_LIMIT, Limit, Offset, qobuz

FavoriteType = Literal["albums", "artists", "tracks"]


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
