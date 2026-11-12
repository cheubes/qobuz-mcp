from typing import Annotated, Literal

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.models import (
    AlbumDetail,
    AlbumSummary,
    ArtistDetail,
    ArtistSummary,
    Genre,
    LabelDetail,
    Page,
    PlaylistDetail,
    PlaylistSummary,
    TrackDetail,
    TrackSummary,
    album_detail,
    album_summary,
    artist_detail,
    artist_summary,
    genre,
    label_detail,
    page_fields,
    playlist_detail,
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


async def get_playlist(
    ctx: Context,
    playlist_id: Annotated[int, Field(ge=1, description="Qobuz playlist ID (an integer).")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> PlaylistDetail:
    """Get a playlist's details and its entries, paginated with `limit` and `offset`.

    Each entry has a `playlist_track_id`, which identifies that entry in the playlist (the same
    track can appear twice), and the track itself with its `id`. Removing or moving entries
    takes `playlist_track_id` values.
    """
    payload = await qobuz(ctx).get_playlist(playlist_id, limit=limit, offset=offset)
    return playlist_detail(payload, limit=limit, offset=offset)


async def get_artist(
    ctx: Context,
    artist_id: Annotated[int, Field(ge=1, description="Qobuz artist ID (an integer).")],
    full_biography: Annotated[
        bool, Field(description="Also return the full biography, which can be long.")
    ] = False,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> ArtistDetail:
    """Get an artist's biography summary and discography.

    The full biography (often several thousand characters) is returned only when
    `full_biography` is true: ask for it when the user wants to know more about the artist.
    The discography is paginated with `limit` and `offset`; `albums.total` tells whether more
    albums exist. Use `get_similar_artists` to discover related artists.
    """
    payload = await qobuz(ctx).get_artist(artist_id, limit=limit, offset=offset)
    return artist_detail(payload, full_biography=full_biography, limit=limit, offset=offset)


async def get_similar_artists(
    ctx: Context,
    artist_id: Annotated[int, Field(ge=1, description="Qobuz artist ID (an integer).")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[ArtistSummary]:
    """List artists similar to a given artist, as Qobuz suggests them, to discover new music."""
    payload = await qobuz(ctx).get_similar_artists(artist_id, limit=limit, offset=offset)
    return Page[ArtistSummary](
        **page_fields(payload.get("artists"), artist_summary, limit=limit, offset=offset)
    )


async def get_label(
    ctx: Context,
    label_id: Annotated[int, Field(ge=1, description="Qobuz label ID (an integer).")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> LabelDetail:
    """Get a record label's description and its albums.

    The albums are paginated with `limit` and `offset`; `albums.total` tells whether more
    albums exist.
    """
    payload = await qobuz(ctx).get_label(label_id, limit=limit, offset=offset)
    return label_detail(payload, limit=limit, offset=offset)


async def list_genres(
    ctx: Context,
    parent_genre_id: Annotated[
        int | None,
        Field(ge=1, description="List the sub-genres of this genre. Omit for top-level genres."),
    ] = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[Genre]:
    """List Qobuz genres, one level of the tree at a time.

    Each genre's `path` holds its ancestor genre IDs, from the root to its direct parent.
    Genre IDs filter `list_featured_albums` and `list_featured_playlists`.
    """
    payload = await qobuz(ctx).list_genres(parent_genre_id, limit=limit, offset=offset)
    return Page[Genre](**page_fields(payload.get("genres"), genre, limit=limit, offset=offset))
