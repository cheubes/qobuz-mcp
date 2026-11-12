"""Tool results: the contract the assistant sees (technical specifications, "Output models")."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

OPEN_QOBUZ_URL = "https://open.qobuz.com"
WEB_PLAYER_URL = "https://play.qobuz.com"


class WriteResult(BaseModel):
    status: str


def write_result(raw: dict[str, Any]) -> WriteResult:
    return WriteResult(status=str(raw.get("status", "unknown")))


def public_url(kind: str, item_id: str | int) -> str:
    return f"{OPEN_QOBUZ_URL}/{kind}/{item_id}"


def web_player_url(kind: str, item_id: str | int) -> str:
    """Awards and stories have no open.qobuz.com route: their web player page is used."""
    return f"{WEB_PLAYER_URL}/{kind}/{item_id}"


class Page[T: BaseModel](BaseModel):
    items: list[T]
    has_more: bool
    total: int | None
    limit: int
    offset: int


class Favorite[T: BaseModel](BaseModel):
    item: T
    favorited_at: str | None


class ArtistRef(BaseModel):
    id: int
    name: str


class ArtistCredit(BaseModel):
    id: int
    name: str
    roles: list[str]


class LabelRef(BaseModel):
    id: int
    name: str


class GenreRef(BaseModel):
    id: int
    name: str


class AlbumRef(BaseModel):
    id: str
    title: str


class OwnerRef(BaseModel):
    id: int
    name: str


class AudioQuality(BaseModel):
    bit_depth: int | None
    sampling_rate_khz: float | None
    channels: int | None
    hires: bool | None


class AlbumSummary(BaseModel):
    id: str
    url: str
    title: str
    version: str | None
    artist: ArtistRef | None
    release_date: str | None
    tracks_count: int | None
    duration_seconds: int | None
    genre: GenreRef | None
    label: LabelRef | None
    audio_quality: AudioQuality
    parental_warning: bool | None
    streamable: bool | None


class Award(BaseModel):
    name: str
    publication_name: str | None
    awarded_at: str | None


class Booklet(BaseModel):
    name: str | None
    url: str


class TrackSummary(BaseModel):
    id: int
    url: str
    title: str
    version: str | None
    performer: ArtistRef | None
    album: AlbumRef | None
    track_number: int | None
    media_number: int | None
    duration_seconds: int | None
    audio_quality: AudioQuality
    parental_warning: bool | None
    streamable: bool | None


class TrackDetail(TrackSummary):
    composer: ArtistRef | None
    work: str | None
    credits: str | None
    isrc: str | None
    copyright: str | None
    release_date: str | None


class AlbumDetail(AlbumSummary):
    artists: list[ArtistCredit]
    composer: ArtistRef | None
    release_type: str | None
    description: str | None
    awards: list[Award]
    booklets: list[Booklet]
    copyright: str | None
    upc: str | None
    tracks: Page[TrackSummary]


class ArtistSummary(BaseModel):
    id: int
    url: str
    name: str
    albums_count: int | None


class ArtistDetail(ArtistSummary):
    biography: str | None
    biography_truncated: bool
    albums: Page[AlbumSummary]


class LabelDetail(BaseModel):
    id: int
    url: str
    name: str
    description: str | None
    albums: Page[AlbumSummary]


class AwardSummary(BaseModel):
    id: int
    url: str
    name: str
    publication_name: str | None


class AwardDetail(BaseModel):
    id: int
    url: str
    name: str
    albums: Page[AlbumSummary]


class Genre(BaseModel):
    id: int
    name: str
    path: list[int]


class PlaylistSummary(BaseModel):
    id: int
    url: str
    name: str
    description: str | None
    owner: OwnerRef | None
    tracks_count: int | None
    duration_seconds: int | None
    is_public: bool | None
    is_collaborative: bool | None
    updated_at: str | None


class PlaylistEntry(BaseModel):
    playlist_track_id: int
    position: int | None
    track: TrackSummary


class PlaylistDetail(PlaylistSummary):
    genres: list[GenreRef]
    entries: Page[PlaylistEntry]


def page_fields(
    group: Any, mapper: Callable[[dict[str, Any]], BaseModel], *, limit: int, offset: int
) -> dict[str, Any]:
    """Fields of a `Page` built from a Qobuz list object, with `limit` and `offset` filled from
    the request when Qobuz omits them. Callers build the concrete `Page[...]`, so the output
    schema matches the result."""
    group = group if isinstance(group, dict) else {}
    items = [mapper(raw) for raw in group.get("items") or []]
    total = group.get("total")
    total = total if isinstance(total, int) else None
    offset = group.get("offset", offset)
    has_more = group.get("has_more")
    if not isinstance(has_more, bool):
        has_more = total is not None and offset + len(items) < total
    return {
        "items": items,
        "has_more": has_more,
        "total": total,
        "limit": group.get("limit", limit),
        "offset": offset,
    }


def fixed_page_fields(
    raw_items: Any, mapper: Callable[[dict[str, Any]], BaseModel]
) -> dict[str, Any]:
    """Fields of a `Page` holding a whole fixed list, such as a radio (ADR-0032)."""
    items = [mapper(raw) for raw in raw_items or []]
    return {
        "items": items,
        "has_more": False,
        "total": len(items),
        "limit": len(items),
        "offset": 0,
    }


def _ref[R: ArtistRef | LabelRef | GenreRef | OwnerRef](model: type[R], raw: Any) -> R | None:
    if not isinstance(raw, dict) or raw.get("id") is None or raw.get("name") is None:
        return None
    return model(id=raw["id"], name=raw["name"])


def _album_ref(raw: Any) -> AlbumRef | None:
    if not isinstance(raw, dict) or raw.get("id") is None or raw.get("title") is None:
        return None
    return AlbumRef(id=str(raw["id"]), title=raw["title"])


def _audio_quality(raw: dict[str, Any]) -> AudioQuality:
    return AudioQuality(
        bit_depth=raw.get("maximum_bit_depth"),
        sampling_rate_khz=raw.get("maximum_sampling_rate"),
        channels=raw.get("maximum_channel_count"),
        hires=raw.get("hires"),
    )


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, int | float):
        return None
    return datetime.fromtimestamp(value, UTC).isoformat()


def favorited_at(raw: dict[str, Any]) -> str | None:
    return _timestamp(raw.get("favorited_at"))


def album_summary(raw: dict[str, Any]) -> AlbumSummary:
    return AlbumSummary(
        id=str(raw["id"]),
        url=public_url("album", raw["id"]),
        title=raw["title"],
        version=raw.get("version"),
        artist=_ref(ArtistRef, raw.get("artist")),
        release_date=raw.get("release_date_original"),
        tracks_count=raw.get("tracks_count"),
        duration_seconds=raw.get("duration"),
        genre=_ref(GenreRef, raw.get("genre")),
        label=_ref(LabelRef, raw.get("label")),
        audio_quality=_audio_quality(raw),
        parental_warning=raw.get("parental_warning"),
        streamable=raw.get("streamable"),
    )


def track_summary(raw: dict[str, Any]) -> TrackSummary:
    return TrackSummary(
        id=raw["id"],
        url=public_url("track", raw["id"]),
        title=raw["title"],
        version=raw.get("version"),
        performer=_ref(ArtistRef, raw.get("performer")),
        album=_album_ref(raw.get("album")),
        track_number=raw.get("track_number"),
        media_number=raw.get("media_number"),
        duration_seconds=raw.get("duration"),
        audio_quality=_audio_quality(raw),
        parental_warning=raw.get("parental_warning"),
        streamable=raw.get("streamable"),
    )


def track_detail(raw: dict[str, Any]) -> TrackDetail:
    return TrackDetail(
        **track_summary(raw).model_dump(),
        composer=_ref(ArtistRef, raw.get("composer")),
        work=raw.get("work"),
        # Qobuz formats the credits as one undocumented string: returned as is, not parsed.
        credits=raw.get("performers"),
        isrc=raw.get("isrc"),
        copyright=raw.get("copyright"),
        release_date=raw.get("release_date_original"),
    )


def playlist_entry(raw: dict[str, Any]) -> PlaylistEntry:
    return PlaylistEntry(
        playlist_track_id=raw["playlist_track_id"],
        position=raw.get("position"),
        track=track_summary(raw),
    )


def playlist_detail(raw: dict[str, Any], *, limit: int, offset: int) -> PlaylistDetail:
    genres = [_ref(GenreRef, genre) for genre in raw.get("genres") or []]
    return PlaylistDetail(
        **playlist_summary(raw).model_dump(),
        genres=[genre for genre in genres if genre is not None],
        entries=Page[PlaylistEntry](
            **page_fields(raw.get("tracks"), playlist_entry, limit=limit, offset=offset)
        ),
    )


def album_detail(raw: dict[str, Any], *, limit: int, offset: int) -> AlbumDetail:
    album = {"id": raw["id"], "title": raw["title"]}

    def album_track(track: dict[str, Any]) -> TrackSummary:
        return track_summary({"album": album, **track})

    return AlbumDetail(
        **album_summary(raw).model_dump(),
        artists=[
            ArtistCredit(id=artist["id"], name=artist["name"], roles=artist.get("roles") or [])
            for artist in raw.get("artists") or []
            if artist.get("id") is not None and artist.get("name") is not None
        ],
        composer=_ref(ArtistRef, raw.get("composer")),
        release_type=raw.get("release_type"),
        description=raw.get("description"),
        awards=[
            Award(
                name=award["name"],
                publication_name=award.get("publication_name"),
                awarded_at=_timestamp(award.get("awarded_at")),
            )
            for award in raw.get("awards") or []
            if award.get("name") is not None
        ],
        booklets=[
            Booklet(name=goodie.get("name"), url=goodie["url"])
            for goodie in raw.get("goodies") or []
            if goodie.get("url")
        ],
        copyright=raw.get("copyright"),
        upc=raw.get("upc"),
        tracks=Page[TrackSummary](
            **page_fields(raw.get("tracks"), album_track, limit=limit, offset=offset)
        ),
    )


def artist_summary(raw: dict[str, Any]) -> ArtistSummary:
    return ArtistSummary(
        id=raw["id"],
        url=public_url("artist", raw["id"]),
        name=raw["name"],
        albums_count=raw.get("albums_count"),
    )


BIOGRAPHY_EXCERPT_CHARACTERS = 1000


def biography_excerpt(text: str) -> tuple[str, bool]:
    """The longest prefix of at most 1,000 characters ending right after a sentence end, or at
    the last whitespace when none fits, and whether text was cut (ADR-0036)."""
    if len(text) <= BIOGRAPHY_EXCERPT_CHARACTERS:
        return text, False
    window = text[:BIOGRAPHY_EXCERPT_CHARACTERS]
    sentence_end = max(window.rfind(mark) for mark in ".!?")
    if sentence_end >= 0:
        return window[: sentence_end + 1], True
    whitespace = max(window.rfind(space) for space in " \t\n")
    return (window[:whitespace] if whitespace > 0 else window), True


def artist_detail(
    raw: dict[str, Any], releases: dict[str, Any], *, full_biography: bool, limit: int, offset: int
) -> ArtistDetail:
    """An artist from `artist/page`, with releases from `artist/getReleasesList` (ADR-0036)."""
    biography = raw.get("biography")
    content = biography.get("content") if isinstance(biography, dict) else None
    truncated = False
    if isinstance(content, str) and not full_biography:
        content, truncated = biography_excerpt(content)
    return ArtistDetail(
        **current_artist_summary(raw).model_dump(),
        biography=content if isinstance(content, str) else None,
        biography_truncated=truncated,
        albums=Page[AlbumSummary](
            **page_fields(releases, current_album_summary, limit=limit, offset=offset)
        ),
    )


def label_detail(
    raw: dict[str, Any], albums: dict[str, Any], *, limit: int, offset: int
) -> LabelDetail:
    """A label from `label/page`, with its albums from `label/getAlbums` (ADR-0034)."""
    return LabelDetail(
        id=raw["id"],
        url=public_url("label", raw["id"]),
        name=raw["name"],
        description=raw.get("description"),
        albums=Page[AlbumSummary](
            **page_fields(albums, current_album_summary, limit=limit, offset=offset)
        ),
    )


def genre(raw: dict[str, Any]) -> Genre:
    # Qobuz's path starts with the genre itself and climbs to the root.
    ancestors = [genre_id for genre_id in raw.get("path") or [] if genre_id != raw["id"]]
    return Genre(id=raw["id"], name=raw["name"], path=list(reversed(ancestors)))


def _display_name(value: Any) -> Any:
    """Names of the current web player format are either strings or `{"display": ...}`."""
    return value.get("display") if isinstance(value, dict) else value


def _current_artist(raw: dict[str, Any]) -> ArtistRef | None:
    artist = raw.get("artist")
    if not isinstance(artist, dict):
        artists = raw.get("artists") or []
        artist = artists[0] if artists else None
    if not isinstance(artist, dict):
        return None
    return _ref(ArtistRef, {"id": artist.get("id"), "name": _display_name(artist.get("name"))})


def _current_audio_quality(raw: dict[str, Any]) -> AudioQuality:
    audio = raw.get("audio_info") or {}
    rights = raw.get("rights") or {}
    return AudioQuality(
        bit_depth=audio.get("maximum_bit_depth"),
        sampling_rate_khz=audio.get("maximum_sampling_rate"),
        channels=audio.get("maximum_channel_count"),
        hires=rights.get("hires_streamable"),
    )


def current_album_summary(raw: dict[str, Any]) -> AlbumSummary:
    """Album of the current web player endpoints (technical specifications, section 10)."""
    dates = raw.get("dates") or {}
    rights = raw.get("rights") or {}
    tracks_count = raw.get("track_count")
    if tracks_count is None:
        tracks_count = raw.get("tracks_count")
    return AlbumSummary(
        id=str(raw["id"]),
        url=public_url("album", raw["id"]),
        title=raw["title"],
        version=raw.get("version"),
        artist=_current_artist(raw),
        release_date=dates.get("original"),
        tracks_count=tracks_count,
        duration_seconds=raw.get("duration"),
        genre=_ref(GenreRef, raw.get("genre")),
        label=_ref(LabelRef, raw.get("label")),
        audio_quality=_current_audio_quality(raw),
        parental_warning=raw.get("parental_warning"),
        streamable=rights.get("streamable"),
    )


def current_track_summary(raw: dict[str, Any]) -> TrackSummary:
    """Track of the current web player endpoints (technical specifications, section 10)."""
    support = raw.get("physical_support") or {}
    rights = raw.get("rights") or {}
    return TrackSummary(
        id=raw["id"],
        url=public_url("track", raw["id"]),
        title=raw["title"],
        version=raw.get("version"),
        performer=_current_artist(raw),
        album=_album_ref(raw.get("album")),
        track_number=support.get("track_number"),
        media_number=support.get("media_number"),
        duration_seconds=raw.get("duration"),
        audio_quality=_current_audio_quality(raw),
        parental_warning=raw.get("parental_warning"),
        streamable=rights.get("streamable"),
    )


def current_playlist_summary(raw: dict[str, Any]) -> PlaylistSummary:
    """Playlist of the current web player endpoints (technical specifications, section 10)."""
    return PlaylistSummary(
        id=raw["id"],
        url=public_url("playlist", raw["id"]),
        name=raw.get("name") or raw["title"],
        description=raw.get("description"),
        owner=_ref(OwnerRef, raw.get("owner")),
        tracks_count=raw.get("tracks_count"),
        duration_seconds=raw.get("duration"),
        is_public=None,
        is_collaborative=None,
        updated_at=_timestamp(raw.get("updated_at")),
    )


def current_artist_summary(raw: dict[str, Any]) -> ArtistSummary:
    """Artist of the current web player endpoints (technical specifications, section 10)."""
    return ArtistSummary(
        id=raw["id"],
        url=public_url("artist", raw["id"]),
        name=_display_name(raw["name"]),
        albums_count=None,
    )


def award_summary(raw: dict[str, Any]) -> AwardSummary:
    magazine = raw.get("magazine")
    return AwardSummary(
        id=raw["id"],
        url=web_player_url("award", raw["id"]),
        name=raw["name"],
        publication_name=magazine.get("name") if isinstance(magazine, dict) else None,
    )


def award_detail(
    raw: dict[str, Any], albums: dict[str, Any], *, limit: int, offset: int
) -> AwardDetail:
    """An award from `award/page`, with its albums from `award/getAlbums`."""
    return AwardDetail(
        id=raw["id"],
        url=web_player_url("award", raw["id"]),
        name=raw["name"],
        albums=Page[AlbumSummary](
            **page_fields(albums, current_album_summary, limit=limit, offset=offset)
        ),
    )


def playlist_summary(raw: dict[str, Any]) -> PlaylistSummary:
    return PlaylistSummary(
        id=raw["id"],
        url=public_url("playlist", raw["id"]),
        name=raw["name"],
        description=raw.get("description"),
        owner=_ref(OwnerRef, raw.get("owner")),
        tracks_count=raw.get("tracks_count"),
        duration_seconds=raw.get("duration"),
        is_public=raw.get("is_public"),
        is_collaborative=raw.get("is_collaborative"),
        updated_at=_timestamp(raw.get("updated_at")),
    )
