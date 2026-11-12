from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from qobuz_mcp.models import PlaylistSummary, WriteResult, playlist_summary, write_result
from qobuz_mcp.tools.common import qobuz

PlaylistId = Annotated[int, Field(ge=1, description="Qobuz ID of a playlist the user owns.")]
AnyPlaylistId = Annotated[int, Field(ge=1, description="Qobuz playlist ID (an integer).")]
PlaylistTrackIds = Annotated[
    list[int],
    Field(
        min_length=1,
        description="`playlist_track_id` values from `get_playlist`, not track IDs.",
    ),
]


async def create_playlist(
    ctx: Context,
    name: Annotated[str, Field(min_length=1, description="Name of the new playlist.")],
    description: Annotated[str, Field(description="Description of the playlist.")] = "",
    is_public: Annotated[
        bool, Field(description="Make the playlist public. Only when the user asks for it.")
    ] = False,
    is_collaborative: Annotated[
        bool, Field(description="Let other users edit it. Only when the user asks for it.")
    ] = False,
) -> PlaylistSummary:
    """Create a playlist owned by the user, private and non-collaborative unless requested.

    Returns the new playlist with its ID, to add tracks with `add_tracks_to_playlist`.
    """
    payload = await qobuz(ctx).create_playlist(
        name, description, is_public=is_public, is_collaborative=is_collaborative
    )
    return playlist_summary(payload)


async def update_playlist(
    ctx: Context,
    playlist_id: PlaylistId,
    name: Annotated[str | None, Field(min_length=1, description="New name.")] = None,
    description: Annotated[str | None, Field(description="New description.")] = None,
    is_public: Annotated[bool | None, Field(description="New visibility.")] = None,
    is_collaborative: Annotated[
        bool | None, Field(description="Whether other users can edit it.")
    ] = None,
) -> PlaylistSummary:
    """Change a playlist's name, description, visibility or collaborative flag.

    Only the fields given are changed; the others keep their current value.
    """
    if name is None and description is None and is_public is None and is_collaborative is None:
        raise ToolError("Give at least one field to change.")
    payload = await qobuz(ctx).update_playlist(
        playlist_id,
        name=name,
        description=description,
        is_public=is_public,
        is_collaborative=is_collaborative,
    )
    return playlist_summary(payload)


async def add_tracks_to_playlist(
    ctx: Context,
    playlist_id: PlaylistId,
    track_ids: Annotated[
        list[int], Field(min_length=1, description="Qobuz track IDs, in the order to add them.")
    ],
) -> PlaylistSummary:
    """Append tracks at the end of a playlist the user owns, in the given order."""
    return playlist_summary(await qobuz(ctx).add_tracks_to_playlist(playlist_id, track_ids))


async def remove_tracks_from_playlist(
    ctx: Context,
    playlist_id: PlaylistId,
    playlist_track_ids: PlaylistTrackIds,
) -> PlaylistSummary:
    """Remove entries from a playlist the user owns.

    Entries are identified by `playlist_track_id`, so only the targeted occurrence of a track
    that appears several times is removed.
    """
    payload = await qobuz(ctx).remove_tracks_from_playlist(playlist_id, playlist_track_ids)
    return playlist_summary(payload)


async def move_playlist_tracks(
    ctx: Context,
    playlist_id: PlaylistId,
    playlist_track_ids: PlaylistTrackIds,
    insert_before: Annotated[
        int,
        Field(
            ge=0,
            description=(
                "1-based position of the entry to move them in front of; 0 moves them first, "
                "`tracks_count + 1` moves them last."
            ),
        ),
    ],
) -> PlaylistSummary:
    """Reorder entries within a playlist the user owns.

    The entries, identified by `playlist_track_id`, are moved in front of the entry currently
    at position `insert_before` (positions as returned by `get_playlist`, starting at 1).
    """
    payload = await qobuz(ctx).move_playlist_tracks(playlist_id, playlist_track_ids, insert_before)
    return playlist_summary(payload)


async def delete_playlist(ctx: Context, playlist_id: PlaylistId) -> WriteResult:
    """Delete a playlist the user owns. This cannot be undone.

    To stop following someone else's playlist, use `unfollow_playlist` instead.
    """
    return write_result(await qobuz(ctx).delete_playlist(playlist_id))


async def follow_playlist(ctx: Context, playlist_id: AnyPlaylistId) -> WriteResult:
    """Follow a playlist, such as an editorial or another user's playlist.

    Followed playlists appear in `list_my_playlists`.
    """
    return write_result(await qobuz(ctx).follow_playlist(playlist_id))


async def unfollow_playlist(ctx: Context, playlist_id: AnyPlaylistId) -> WriteResult:
    """Stop following a playlist. The playlist itself is not deleted."""
    return write_result(await qobuz(ctx).unfollow_playlist(playlist_id))
