"""Binary MoIP command-line interface."""

from __future__ import annotations

import argparse
import sys

from binary_moip import __version__
from binary_moip.cli import config as config_cmd
from binary_moip.cli import control as control_cmd
from binary_moip.cli.context import resolve_options


def build_parser() -> argparse.ArgumentParser:
    """Build the root argument parser."""
    parser = argparse.ArgumentParser(
        prog="binary-moip",
        description="CLI for SnapAV Binary MoIP control (TCP) and configuration (REST) APIs",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    parser.add_argument("--host", help="Controller host (env: MOIP_HOST)")
    parser.add_argument("--base-url", help="REST base URL (env: MOIP_BASE_URL, default: https://HOST)")
    parser.add_argument("--user", help="Username (env: MOIP_USER; optional for control commands)")
    parser.add_argument(
        "--password",
        help="Password (env: MOIP_PASS; prompts if unset for config commands)",
    )
    parser.add_argument("--port", type=int, default=23, help="TCP control port (default: 23)")
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable SSL certificate verification for REST API",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="Connection timeout in seconds")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    subparsers = parser.add_subparsers(dest="command", required=True)
    control_cmd.register(subparsers)
    config_cmd.register(subparsers)

    return parser


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.password is not None:
        print(
            "Warning: passing --password on the command line exposes it to other "
            "users via the process list; prefer the MOIP_PASS environment variable "
            "or the interactive prompt.",
            file=sys.stderr,
        )

    # The TCP control API may not require authentication, so credentials are only
    # mandatory for the REST-based config commands.
    require_credentials = args.command == "config"

    try:
        options = resolve_options(
            host=args.host,
            base_url=args.base_url,
            user=args.user,
            password=args.password,
            port=args.port,
            no_verify_ssl=args.no_verify_ssl,
            timeout=args.timeout,
            pretty=args.pretty,
            require_credentials=require_credentials,
        )
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    if args.command == "control":
        control_cmd.run_control(args, options)
    elif args.command == "config":
        config_cmd.run_config(args, options)


if __name__ == "__main__":
    main()
