from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.models import (
    AlbumDetail,
    AlbumSummary,
    ArtistSummary,
    Page,
    PlaylistSummary,
    TrackDetail,
    TrackSummary,
    album_detail,
    album_summary,
    artist_summary,
    page_fields,
    playlist_summary,
    track_detail,
    track_summary,
)
from qobuz_mcp.tools.common import DEFAULT_LIMIT, Limit, Offset, qobuz

SearchType = Literal["albums", "artists", "tracks", "playlists"]


async def search_catalog(
    ctx: Context,
    query: Annotated[str, Field(min_length=1, description="Free-text search, as on Qobuz.")],
    type: Annotated[SearchType, Field(description="Kind of items to search for.")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[AlbumSummary] | Page[ArtistSummary] | Page[TrackSummary] | Page[PlaylistSummary]:
    """Search the Qobuz catalog for albums, artists, tracks or playlists.

    Returns one page of items of the requested type, with their Qobuz IDs and public URLs.
    Use the IDs with the other tools, for example `get_album` for an album.
    """
    payload = await qobuz(ctx).search_catalog(query, type, limit=limit, offset=offset)
    group = payload.get(type)
    match type:
        case "albums":
            return Page[AlbumSummary](
                **page_fields(group, album_summary, limit=limit, offset=offset)
            )
        case "artists":
            return Page[ArtistSummary](
                **page_fields(group, artist_summary, limit=limit, offset=offset)
            )
        case "tracks":
            return Page[TrackSummary](
                **page_fields(group, track_summary, limit=limit, offset=offset)
            )
        case "playlists":
            return Page[PlaylistSummary](
                **page_fields(group, playlist_summary, limit=limit, offset=offset)
            )


async def get_album(
    ctx: Context,
    album_id: Annotated[str, Field(min_length=1, description="Qobuz album ID (a string).")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AlbumDetail:
    """Get an album's details: tracklist, audio quality, artists and roles, label, genre,
    release date, description, press awards and booklet links.

    The tracklist is paginated with `limit` and `offset`; `tracks.total` tells whether more
    tracks exist.
    """
    payload = await qobuz(ctx).get_album(album_id, limit=limit, offset=offset)
    return album_detail(payload, limit=limit, offset=offset)


async def get_track(
    ctx: Context,
    track_id: Annotated[int, Field(ge=1, description="Qobuz track ID (an integer).")],
) -> TrackDetail:
    """Get a track's details: main performer, credits, composer, work, album, audio quality,
    ISRC and release date.

    `credits` is Qobuz's own text listing every contributor with their roles.
    """
    return track_detail(await qobuz(ctx).get_track(track_id))
