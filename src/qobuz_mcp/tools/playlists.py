from typing import Annotated

from fastmcp import Context
from fastmcp.exceptions import ToolError
from pydantic import Field

from qobuz_mcp.models import PlaylistSummary, playlist_summary
from qobuz_mcp.tools.common import qobuz

PlaylistId = Annotated[int, Field(ge=1, description="Qobuz ID of a playlist the user owns.")]


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
