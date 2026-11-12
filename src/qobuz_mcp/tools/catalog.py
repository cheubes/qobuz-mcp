from typing import Annotated, Any, Literal

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.api import DISCOVER_ALBUM_ENDPOINTS
from qobuz_mcp.models import (
    AlbumDetail,
    AlbumSummary,
    ArtistDetail,
    ArtistSummary,
    AwardDetail,
    AwardSummary,
    Genre,
    LabelDetail,
    Page,
    PlaylistDetail,
    PlaylistSummary,
    StorySummary,
    TrackDetail,
    TrackSummary,
    album_detail,
    album_summary,
    artist_detail,
    artist_summary,
    award_detail,
    award_summary,
    current_album_summary,
    current_artist_summary,
    current_playlist_summary,
    current_track_summary,
    fixed_page_fields,
    genre,
    label_detail,
    page_fields,
    playlist_detail,
    playlist_summary,
    story_summary,
    track_detail,
    track_summary,
)
from qobuz_mcp.tools.common import DEFAULT_LIMIT, Limit, Offset, qobuz

SearchType = Literal["albums", "artists", "tracks", "playlists"]

# The values album/getFeatured accepts, as listed by the API itself, plus album-of-the-week,
# served by discover/albumOfTheWeek (ADR-0035).
FeaturedAlbumCategory = Literal[
    "album-of-the-week",
    "new-releases",
    "new-releases-full",
    "recent-releases",
    "press-awards",
    "best-sellers",
    "most-streamed",
    "editor-picks",
    "most-featured",
    "ideal-discography",
    "qobuzissims",
    "harmonia-mundi",
    "universal-classic",
    "universal-jazz",
    "universal-jeunesse",
    "universal-chanson",
]

# The slugs playlist/getTags returned when observed (ADR-0033).
PlaylistTag = Literal[
    "hi-res",
    "new",
    "focus",
    "mood",
    "artist",
    "danslecasque",
    "label",
    "qobuzdigs",
    "event",
    "auditoriums",
    "speakers",
    "ideal-discography",
    "popular",
]

# The release types artist/getReleasesList accepts, except `all` (no filter) and `download`,
# whose meaning is not documented.
ReleaseType = Literal["album", "live", "compilation", "epSingle", "other", "awardedRelease", "next"]

GenreFilter = Annotated[
    int | None, Field(ge=1, description="Only items of this genre (an ID from `list_genres`).")
]


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

    The tracklist is paginated with `limit` and `offset`; `tracks.has_more` tells whether more
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
        bool, Field(description="Return the full biography, which can be long, not an excerpt.")
    ] = False,
    release_type: Annotated[
        ReleaseType | None,
        Field(
            description=(
                "Only releases of this type: album, live, compilation, epSingle (EPs and "
                "singles), other, awardedRelease (releases with a press award), next (upcoming "
                "releases). Omit for the whole discography."
            )
        ),
    ] = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> ArtistDetail:
    """Get an artist's biography and discography, newest releases first.

    By default, `biography` is the start of the biography, at most 1,000 characters cut at a
    sentence end, and `biography_truncated` tells whether text was cut. Set `full_biography`
    when the user wants to know more about the artist: the full text can reach several
    thousand characters. The discography is paginated with `limit` and `offset`;
    `albums.has_more` tells whether more releases exist. Use `get_similar_artists` to discover
    related artists.
    """
    client = qobuz(ctx)
    artist = await client.get_artist(artist_id)
    releases = await client.list_artist_releases(
        artist_id, release_type, limit=limit, offset=offset
    )
    return artist_detail(
        artist, releases, full_biography=full_biography, limit=limit, offset=offset
    )


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

    The albums are paginated with `limit` and `offset`; `albums.has_more` tells whether more
    albums exist.
    """
    client = qobuz(ctx)
    label = await client.get_label(label_id)
    albums = await client.list_label_albums(label_id, limit=limit, offset=offset)
    return label_detail(label, albums, limit=limit, offset=offset)


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


async def list_featured_albums(
    ctx: Context,
    category: Annotated[
        FeaturedAlbumCategory,
        Field(
            description=(
                "Editorial list: new releases, press awards, best sellers, most streamed, "
                "editor picks, ideal discography, Qobuzissimes, album of the week, or a label "
                "selection."
            )
        ),
    ],
    genre_id: GenreFilter = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[AlbumSummary]:
    """List albums from one of Qobuz's editorial selections, optionally for one genre."""
    payload = await qobuz(ctx).list_featured_albums(category, genre_id, limit=limit, offset=offset)
    if category in DISCOVER_ALBUM_ENDPOINTS:
        return Page[AlbumSummary](
            **page_fields(payload, current_album_summary, limit=limit, offset=offset)
        )
    return Page[AlbumSummary](
        **page_fields(payload.get("albums"), album_summary, limit=limit, offset=offset)
    )


async def list_featured_playlists(
    ctx: Context,
    genre_id: GenreFilter = None,
    tag: Annotated[
        PlaylistTag | None,
        Field(
            description=(
                "Only playlists with this tag: hi-res, new (new releases), focus, mood, artist, "
                "danslecasque (listening with...), label (label stories), qobuzdigs, event "
                "(events and media), auditoriums (hi-fi audio partners), speakers (test your "
                "speakers), ideal-discography, popular (top playlists)."
            )
        ),
    ] = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[PlaylistSummary]:
    """List Qobuz's editorial playlists, optionally for one genre or one tag.

    Use `get_playlist` to see a playlist's tracks.
    """
    payload = await qobuz(ctx).list_featured_playlists(genre_id, tag, limit=limit, offset=offset)
    return Page[PlaylistSummary](
        **page_fields(payload, current_playlist_summary, limit=limit, offset=offset)
    )


async def list_similar_albums(
    ctx: Context,
    album_id: Annotated[str, Field(min_length=1, description="Qobuz album ID (a string).")],
) -> Page[AlbumSummary]:
    """List albums similar to a given album, as Qobuz recommends them.

    Qobuz returns one fixed list of up to 30 albums, with no further pages.
    """
    payload = await qobuz(ctx).list_similar_albums(album_id)
    albums = payload.get("albums")
    return Page[AlbumSummary](
        **fixed_page_fields(
            albums.get("items") if isinstance(albums, dict) else None, current_album_summary
        )
    )


async def get_radio(
    ctx: Context,
    seed_type: Annotated[
        Literal["album", "artist", "track"], Field(description="What the radio is built from.")
    ],
    seed_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Qobuz ID of the seed: an album ID, or an artist or track ID in digits.",
        ),
    ],
) -> Page[TrackSummary]:
    """Get the tracks of a radio built by Qobuz from an album, an artist or a track.

    Qobuz returns one fixed list of up to 30 tracks, with no further pages. Use
    `suggest_tracks` instead to continue a list of tracks, such as a playlist.
    """
    payload = await qobuz(ctx).get_radio(seed_type, seed_id)
    tracks = payload.get("tracks")
    return Page[TrackSummary](
        **fixed_page_fields(
            tracks.get("items") if isinstance(tracks, dict) else None, current_track_summary
        )
    )


def _suggestion_seed(track: dict[str, Any]) -> dict[str, int]:
    """What `dynamic/suggest` needs to know about a track, `0` standing for a missing ID."""
    album = track.get("album") or {}

    def id_of(value: Any) -> int:
        return value["id"] if isinstance(value, dict) and isinstance(value.get("id"), int) else 0

    return {
        "track_id": track["id"],
        "artist_id": id_of(track.get("performer")),
        "label_id": id_of(album.get("label")),
        "genre_id": id_of(album.get("genre")),
    }


async def suggest_tracks(
    ctx: Context,
    track_ids: Annotated[
        list[int],
        Field(
            min_length=1,
            max_length=10,
            description="1 to 10 Qobuz track IDs to continue, such as the end of a playlist.",
        ),
    ],
    limit: Limit = DEFAULT_LIMIT,
) -> Page[TrackSummary]:
    """Suggest tracks to continue a list of tracks, for example to extend a playlist.

    The given tracks are never suggested. The result is one complete page of up to `limit`
    tracks, with no further pages.
    """
    client = qobuz(ctx)
    seeds = [_suggestion_seed(await client.get_track(track_id)) for track_id in track_ids]
    payload = await client.suggest_tracks(seeds, limit=limit)
    tracks = payload.get("tracks")
    return Page[TrackSummary](
        **fixed_page_fields(
            tracks.get("items") if isinstance(tracks, dict) else None, track_summary
        )
    )


async def list_artist_playlists(
    ctx: Context,
    artist_id: Annotated[int, Field(ge=1, description="Qobuz artist ID (an integer).")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[PlaylistSummary]:
    """List Qobuz's editorial playlists featuring an artist.

    Use `get_playlist` to see a playlist's tracks.
    """
    payload = await qobuz(ctx).list_artist_playlists(artist_id, limit=limit, offset=offset)
    return Page[PlaylistSummary](
        **page_fields(payload, current_playlist_summary, limit=limit, offset=offset)
    )


async def list_label_items(
    ctx: Context,
    label_id: Annotated[int, Field(ge=1, description="Qobuz label ID (an integer).")],
    section: Annotated[
        Literal["top_artists", "upcoming_releases", "playlists", "awarded_releases"],
        Field(
            description=(
                "Which part of the label: its top artists, its upcoming releases, its "
                "editorial playlists, or its releases that received a press award."
            )
        ),
    ],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[ArtistSummary] | Page[AlbumSummary] | Page[PlaylistSummary]:
    """List one section of a record label: artists, albums or playlists, matching `section`.

    Use `get_label` for the label's description and its whole catalog of albums.
    """
    payload = await qobuz(ctx).list_label_items(label_id, section, limit=limit, offset=offset)
    match section:
        case "top_artists":
            return Page[ArtistSummary](
                **page_fields(payload, current_artist_summary, limit=limit, offset=offset)
            )
        case "playlists":
            return Page[PlaylistSummary](
                **page_fields(payload, current_playlist_summary, limit=limit, offset=offset)
            )
        case _:
            return Page[AlbumSummary](
                **page_fields(payload, current_album_summary, limit=limit, offset=offset)
            )


async def list_awards(
    ctx: Context, limit: Limit = DEFAULT_LIMIT, offset: Offset = 0
) -> Page[AwardSummary]:
    """List press awards and distinctions, with the publication that grants them.

    Use `get_award` for an award's albums, and `list_related_stories` for its stories.
    """
    payload = await qobuz(ctx).list_awards(limit=limit, offset=offset)
    return Page[AwardSummary](**page_fields(payload, award_summary, limit=limit, offset=offset))


async def get_award(
    ctx: Context,
    award_id: Annotated[int, Field(ge=1, description="Qobuz award ID, from `list_awards`.")],
    genre_id: GenreFilter = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> AwardDetail:
    """Get a press award and the albums that received it, optionally for one genre.

    The albums are paginated with `limit` and `offset`; `albums.has_more` tells whether more
    albums exist.
    """
    client = qobuz(ctx)
    award = await client.get_award(award_id)
    albums = await client.list_award_albums(award_id, genre_id, limit=limit, offset=offset)
    return award_detail(award, albums, limit=limit, offset=offset)


async def search_stories(
    ctx: Context,
    query: Annotated[str, Field(min_length=1, description="Free-text search in the magazine.")],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[StorySummary]:
    """Search Qobuz magazine stories: news, interviews, reviews.

    Each story comes with its title, summary, authors, date and sections, and a link to read
    it on Qobuz. The full text is not available.
    """
    payload = await qobuz(ctx).search_stories(query, limit=limit, offset=offset)
    return Page[StorySummary](
        **page_fields(payload.get("stories"), story_summary, limit=limit, offset=offset)
    )


async def list_related_stories(
    ctx: Context,
    entity_type: Annotated[
        Literal["album", "artist", "label", "playlist", "award"],
        Field(description="What the stories are about."),
    ],
    entity_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Qobuz ID of that item: an album ID, or another ID in digits.",
        ),
    ],
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[StorySummary]:
    """List Qobuz magazine stories about an album, an artist, a label, a playlist or an award.

    Each story comes with its title, summary, authors, date and sections, and a link to read
    it on Qobuz. The full text is not available.
    """
    payload = await qobuz(ctx).list_related_stories(
        entity_type, entity_id, limit=limit, offset=offset
    )
    return Page[StorySummary](**page_fields(payload, story_summary, limit=limit, offset=offset))
