import re
from pathlib import Path
from typing import Any

import pytest
from fastmcp import Client

from qobuz_mcp import server

pytestmark = pytest.mark.anyio

FUNCTIONAL_SPEC = Path(__file__).resolve().parents[2] / "specs" / "functional-specifications.md"
EXPECTED_HINTS = {
    "read-only": (True, None),
    "additive": (False, False),
    "destructive": (False, True),
}


def specified_tools() -> dict[str, str]:
    """Tool names and annotations from section 5 of the functional specifications."""
    section = FUNCTIONAL_SPEC.read_text().split("## 5. Tools", 1)[1].split("\n## 6.", 1)[0]
    tools: dict[str, str] = {}
    for subsection in re.split(r"\n### ", section)[1:]:
        read_only = "(read-only)" in subsection.splitlines()[0]
        for row in re.findall(r"^\| `([a-z_]+)` \| ([^|]+) \|", subsection, re.MULTILINE):
            name, second_cell = row
            tools[name] = "read-only" if read_only else second_cell.strip()
    return tools


def test_the_specification_lists_32_tools() -> None:
    tools = specified_tools()
    assert len(tools) == 32
    assert set(tools.values()) == set(EXPECTED_HINTS)


async def test_server_exposes_exactly_the_specified_tools_and_annotations() -> None:
    """AC-BEH-01"""
    async with Client(server.mcp) as client:
        exposed: dict[str, Any] = {tool.name: tool for tool in await client.list_tools()}
    expected = specified_tools()
    assert set(exposed) == set(expected)
    for name, annotation in expected.items():
        hints = exposed[name].annotations
        assert hints is not None, name
        assert (hints.read_only_hint, hints.destructive_hint) == EXPECTED_HINTS[annotation], name
        assert hints.open_world_hint is True, name
