import json
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def message(identifier: int | None, method: str, params: dict[str, object]) -> str:
    payload: dict[str, object] = {"jsonrpc": "2.0", "method": method, "params": params}
    if identifier is not None:
        payload["id"] = identifier
    return json.dumps(payload) + "\n"


def test_stdout_only_carries_mcp_messages() -> None:
    """AC-BEH-12"""
    requests = "".join(
        [
            message(
                1,
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"},
                },
            ),
            message(None, "notifications/initialized", {}),
            message(2, "tools/list", {}),
            message(
                3,
                "tools/call",
                {"name": "search_catalog", "arguments": {"query": "x", "type": "albums"}},
            ),
        ]
    )
    # The in-memory keyring backend comes from PYTHON_KEYRING_BACKEND, set in tests/conftest.py:
    # the subprocess starts logged out and never touches the real Keychain or the network.
    process = subprocess.Popen(
        [sys.executable, "-m", "qobuz_mcp", "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        cwd=ROOT,
    )
    watchdog = threading.Timer(60, process.kill)
    watchdog.start()
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(requests)
        process.stdin.flush()
        responses: list[dict[str, object]] = []
        while not {1, 2, 3} <= {response.get("id") for response in responses}:
            line = process.stdout.readline()
            assert line, "the server closed stdout before answering"
            if line.strip():
                responses.append(json.loads(line))
        process.stdin.close()
        remaining = process.stdout.read()
        process.wait(timeout=30)
    finally:
        watchdog.cancel()
        process.kill()
    responses += [json.loads(line) for line in remaining.splitlines() if line.strip()]
    assert all(response.get("jsonrpc") == "2.0" for response in responses)
    by_id = {response.get("id"): response for response in responses}
    assert "search_catalog" in json.dumps(by_id[2])
    assert "Not logged in" in json.dumps(by_id[3])
