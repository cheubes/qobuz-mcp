from typing import Annotated

import httpx2
from fastmcp import Context
from pydantic import Field

from qobuz_mcp.api import QobuzClient
from qobuz_mcp.credentials import load_credentials
from qobuz_mcp.errors import AuthenticationError

DEFAULT_LIMIT = 25
MAX_LIMIT = 100

Limit = Annotated[
    int, Field(ge=1, le=MAX_LIMIT, description=f"Number of items to return, 1 to {MAX_LIMIT}.")
]
Offset = Annotated[int, Field(ge=0, description="Number of items to skip, to fetch next pages.")]


def qobuz(ctx: Context) -> QobuzClient:
    """Build a client from the credentials read now, so login and logout apply at once."""
    credentials = load_credentials()
    if credentials is None:
        raise AuthenticationError("Not logged in. Run `qobuz-mcp login`.")
    http: httpx2.AsyncClient = ctx.lifespan_context["http"]
    return QobuzClient(http, credentials.app_id, credentials.user_auth_token)
