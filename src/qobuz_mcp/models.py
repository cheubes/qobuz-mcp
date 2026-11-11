"""Tool results: the contract the assistant sees (technical specifications, "Output models")."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

OPEN_QOBUZ_URL = "https://open.qobuz.com"


def public_url(kind: str, item_id: str | int) -> str:
    return f"{OPEN_QOBUZ_URL}/{kind}/{item_id}"


class Page[T: BaseModel](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


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


def page_fields(
    group: Any, mapper: Callable[[dict[str, Any]], BaseModel], *, limit: int, offset: int
) -> dict[str, Any]:
    """Fields of a `Page` built from a Qobuz list object, with `limit` and `offset` filled from
    the request when Qobuz omits them. Callers build the concrete `Page[...]`, so the output
    schema matches the result."""
    group = group if isinstance(group, dict) else {}
    items = [mapper(raw) for raw in group.get("items") or []]
    return {
        "items": items,
        "total": group.get("total", len(items)),
        "limit": group.get("limit", limit),
        "offset": group.get("offset", offset),
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
