from typing import Any

import pytest

from qobuz_mcp.models import favorited_at, page_fields


def identity(raw: dict[str, Any]) -> Any:
    return raw


@pytest.mark.parametrize("missing", [False, None, "2024-01-01"])
def test_missing_dates_are_null(missing: Any) -> None:
    assert favorited_at({"favorited_at": missing}) is None


def test_timestamps_are_utc_date_times() -> None:
    assert favorited_at({"favorited_at": 0}) == "1970-01-01T00:00:00+00:00"


@pytest.mark.parametrize("value", [None, "10", True])
def test_unusable_offset_and_limit_are_filled_from_the_request(value: Any) -> None:
    group = {"offset": value, "limit": value, "total": 10, "items": [{}, {}]}
    fields = page_fields(group, identity, limit=2, offset=4)
    assert (fields["offset"], fields["limit"], fields["has_more"]) == (4, 2, True)
