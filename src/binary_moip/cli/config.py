"""REST configuration CLI subcommands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from binary_moip.cli.context import CliOptions, config_client
from binary_moip.cli.output import emit, handle_error
from binary_moip.config.events import ChangeEvent


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register config subcommands."""
    config = subparsers.add_parser("config", help="REST configuration API (v1.3.0)")
    config_sub = config.add_subparsers(dest="config_command", required=True)

    config_sub.add_parser("units", help="List all MoIP units")
    config_sub.add_parser("system", help="Get global system settings")
    config_sub.add_parser("status", help="Get system status summary")

    request = config_sub.add_parser("request", help="Send an arbitrary REST API request")
    request.add_argument("method", help="HTTP method (GET, POST, PUT, DELETE)")
    request.add_argument("path", help="API path (e.g. /api/v1/moip/unit)")
    request.add_argument("--body", help="JSON request body string")
    request.add_argument("--body-file", type=Path, help="Path to JSON request body file")
    request.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Query parameter (repeatable)",
    )

    watch = config_sub.add_parser("watch", help="Watch change events (Ctrl+C to stop)")
    watch.add_argument("--raw", action="store_true", help="Use raw TCP socket instead of WebSocket")


def _parse_body(args: argparse.Namespace) -> dict | None:
    if args.body and args.body_file:
        raise SystemExit("Use only one of --body or --body-file")
    if args.body_file:
        return json.loads(args.body_file.read_text(encoding="utf-8"))
    if args.body:
        return json.loads(args.body)
    return None


def _parse_params(params: list[str]) -> dict[str, str] | None:
    if not params:
        return None
    result: dict[str, str] = {}
    for item in params:
        if "=" not in item:
            raise SystemExit(f"Invalid --param (expected KEY=VALUE): {item}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def _event_to_dict(event: ChangeEvent) -> dict:
    return {"action": event.action, "path": event.path, "raw": event.raw}


def run_config(args: argparse.Namespace, options: CliOptions) -> None:
    """Execute a config subcommand."""
    try:
        with config_client(options) as client:
            if args.config_command == "units":
                emit(client.moip.list_unit(), pretty=options.pretty)
            elif args.config_command == "system":
                emit(client.moip.list_system(), pretty=options.pretty)
            elif args.config_command == "status":
                emit(client.moip.list_status(), pretty=options.pretty)
            elif args.config_command == "request":
                body = _parse_body(args)
                params = _parse_params(args.param)
                result = client.request(
                    args.method.upper(),
                    args.path,
                    params=params,
                    json=body,
                )
                emit(result, pretty=options.pretty)
            elif args.config_command == "watch":
                subscribe = (
                    client.events.subscribe_raw
                    if args.raw
                    else client.events.subscribe_websocket
                )
                for event in subscribe():
                    emit(_event_to_dict(event), pretty=options.pretty)
    except KeyboardInterrupt:
        pass
    except BaseException as exc:
        handle_error(exc)
