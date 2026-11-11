import argparse
import sys
from collections.abc import Sequence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qobuz-mcp", description="Local MCP server for Qobuz.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve", help="Start the MCP server on stdio.")
    login = commands.add_parser("login", help="Sign in to Qobuz and store the credentials.")
    login.add_argument(
        "--token",
        action="store_true",
        help="Paste a token copied from the web player instead of signing in in the browser.",
    )
    commands.add_parser("logout", help="Delete the stored credentials.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    # stdout is reserved for the MCP protocol once `serve` exists.
    print(f"qobuz-mcp {arguments.command}: not implemented yet", file=sys.stderr)
    return 1
