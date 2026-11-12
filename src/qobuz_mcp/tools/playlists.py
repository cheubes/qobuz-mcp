from typing import Annotated

from fastmcp import Context
from pydantic import Field

from qobuz_mcp.models import PlaylistSummary, playlist_summary
from qobuz_mcp.tools.common import qobuz


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
