import runpy
import sys

import keyring
import pytest

from qobuz_mcp import cli, oauth
from qobuz_mcp.credentials import Credentials, load_credentials, save_credentials
from tests.fakes import BUNDLE, FAKE_APP_ID, FAKE_CODE, FAKE_TOKEN, FakeBrowser, FakeQobuz
from tests.memory_keyring import LockedKeyring


@pytest.fixture
def fake_qobuz(monkeypatch: pytest.MonkeyPatch) -> FakeQobuz:
    fake = FakeQobuz()
    monkeypatch.setattr(cli, "_http_client", fake.client)
    monkeypatch.delenv("QOBUZ_APP_ID", raising=False)
    return fake


@pytest.fixture
def browser(monkeypatch: pytest.MonkeyPatch) -> FakeBrowser:
    fake = FakeBrowser()
    monkeypatch.setattr("webbrowser.open", fake.open)
    return fake


def assert_no_secret(output: str) -> None:
    assert FAKE_TOKEN not in output
    assert FAKE_CODE not in output


def test_serve_runs_the_mcp_server(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("qobuz_mcp.server.run", lambda: calls.append("run"))
    assert cli.main(["serve"]) == 0
    assert calls == ["run"]


@pytest.mark.parametrize("argv", [[], ["unknown"]])
def test_invalid_command_exits_with_usage_error(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(argv)
    assert exit_info.value.code == 2


def test_module_entry_point_runs_the_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["qobuz-mcp", "logout"])
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_module("qobuz_mcp", run_name="__main__")
    assert exit_info.value.code == 0


def test_browser_login_stores_the_credentials(
    fake_qobuz: FakeQobuz, browser: FakeBrowser, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-12, AC-SETUP-10"""
    assert cli.main(["login"]) == 0
    assert load_credentials() == Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN)
    captured = capsys.readouterr()
    assert "Logged in as Test User" in captured.out
    assert_no_secret(captured.out + captured.err)


def test_login_without_redirect_times_out_and_stores_nothing(
    fake_qobuz: FakeQobuz, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-13"""
    monkeypatch.setattr(oauth, "LOGIN_TIMEOUT_SECONDS", 0.2)
    monkeypatch.setattr("webbrowser.open", FakeBrowser(code=None).open)
    assert cli.main(["login"]) == 1
    assert load_credentials() is None
    assert "No sign-in completed" in capsys.readouterr().err


def test_rejected_authorization_code_stores_nothing(
    fake_qobuz: FakeQobuz, browser: FakeBrowser, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-15, AC-SETUP-10"""
    fake_qobuz.oauth_status = 401
    assert cli.main(["login"]) == 1
    assert load_credentials() is None
    captured = capsys.readouterr()
    assert "rejected the sign-in" in captured.err
    assert_no_secret(captured.out + captured.err)


@pytest.mark.parametrize("change", ["bundle", "web_player_status"])
def test_missing_app_id_suggests_the_environment_override(
    fake_qobuz: FakeQobuz, change: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-05"""
    if change == "bundle":
        fake_qobuz.bundle = BUNDLE.replace("production:", "elsewhere:")
    else:
        fake_qobuz.web_player_status = 503
    assert cli.main(["login"]) == 1
    assert "QOBUZ_APP_ID" in capsys.readouterr().err
    assert load_credentials() is None


def test_app_id_override_replaces_extraction(
    fake_qobuz: FakeQobuz, browser: FakeBrowser, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_qobuz.bundle = BUNDLE.replace("production:", "elsewhere:")
    monkeypatch.setenv("QOBUZ_APP_ID", "987654321")
    assert cli.main(["login"]) == 0
    credentials = load_credentials()
    assert credentials is not None
    assert credentials.app_id == "987654321"


@pytest.mark.parametrize("change", ["bundle", "web_player_status"])
def test_missing_private_key_suggests_token_login(
    fake_qobuz: FakeQobuz,
    change: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-SETUP-17"""
    if change == "bundle":
        fake_qobuz.bundle = BUNDLE.replace("privateKey", "otherKey")
    else:
        monkeypatch.setenv("QOBUZ_APP_ID", FAKE_APP_ID)
        fake_qobuz.web_player_status = 503
    assert cli.main(["login"]) == 1
    assert "login --token" in capsys.readouterr().err
    assert load_credentials() is None


def test_token_login_stores_a_valid_token(
    fake_qobuz: FakeQobuz, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-03, AC-SETUP-10"""
    monkeypatch.setattr("getpass.getpass", lambda prompt: f" {FAKE_TOKEN} ")
    assert cli.main(["login", "--token"]) == 0
    assert load_credentials() == Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN)
    captured = capsys.readouterr()
    assert_no_secret(captured.out + captured.err)


def test_token_login_rejects_an_invalid_token(
    fake_qobuz: FakeQobuz, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-04"""
    monkeypatch.setattr("getpass.getpass", lambda prompt: "invalid-token")
    assert cli.main(["login", "--token"]) == 1
    assert load_credentials() is None
    captured = capsys.readouterr()
    assert "rejected the token" in captured.err
    assert "invalid-token" not in captured.err


def test_token_login_with_override_skips_the_web_player(
    fake_qobuz: FakeQobuz, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("QOBUZ_APP_ID", FAKE_APP_ID)
    monkeypatch.setattr("getpass.getpass", lambda prompt: FAKE_TOKEN)
    assert cli.main(["login", "--token"]) == 0
    assert fake_qobuz.web_player_requests() == []


def test_logout_removes_the_credentials(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-SETUP-07, AC-SETUP-10"""
    save_credentials(Credentials(app_id=FAKE_APP_ID, user_auth_token=FAKE_TOKEN))
    assert cli.main(["logout"]) == 0
    assert load_credentials() is None
    assert cli.main(["logout"]) == 0
    captured = capsys.readouterr()
    assert "Logged out" in captured.out
    assert "Not logged in" in captured.out
    assert_no_secret(captured.out + captured.err)


def test_locked_keychain_fails_login_and_logout(
    fake_qobuz: FakeQobuz, browser: FakeBrowser, capsys: pytest.CaptureFixture[str]
) -> None:
    """AC-SETUP-20"""
    keyring.set_keyring(LockedKeyring())
    assert cli.main(["login"]) == 1
    assert cli.main(["logout"]) == 1
    captured = capsys.readouterr()
    assert captured.err.count("Could not access the macOS Keychain") == 2
    assert "Not logged in" not in captured.out
    assert_no_secret(captured.out + captured.err)
