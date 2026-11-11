import runpy
import sys

import pytest

from qobuz_mcp.cli import main


@pytest.mark.parametrize("argv", [["serve"], ["login"], ["login", "--token"], ["logout"]])
def test_commands_are_not_implemented_yet(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(argv) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not implemented yet" in captured.err


@pytest.mark.parametrize("argv", [[], ["unknown"]])
def test_invalid_command_exits_with_usage_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 2


def test_module_entry_point_runs_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["qobuz-mcp", "logout"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("qobuz_mcp", run_name="__main__")
    assert exit_info.value.code == 1
