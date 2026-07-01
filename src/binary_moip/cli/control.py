"""TCP control CLI subcommands."""

from __future__ import annotations

import argparse

from binary_moip.cli.context import CliOptions, control_client
from binary_moip.cli.output import emit, emit_raw, handle_error


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register control subcommands."""
    control = subparsers.add_parser("control", help="TCP port-23 control API (v1.9)")
    control_sub = control.add_subparsers(dest="control_command", required=True)

    control_sub.add_parser("devices", help="Get TX and RX device counts")
    control_sub.add_parser("receivers", help="Get current receiver routing")
    control_sub.add_parser("scenes", help="List available scenes")

    names = control_sub.add_parser("names", help="Get device names")
    names_group = names.add_mutually_exclusive_group(required=True)
    names_group.add_argument("--tx", action="store_true", help="List transmitter names")
    names_group.add_argument("--rx", action="store_true", help="List receiver names")

    switch = control_sub.add_parser("switch", help="Switch a receiver to a transmitter")
    switch.add_argument("tx", type=int, help="Transmitter index (0 to disconnect)")
    switch.add_argument("rx", type=int, help="Receiver index")

    activate = control_sub.add_parser("activate-scene", help="Activate a named scene")
    activate.add_argument("name", help="Scene name")

    raw = control_sub.add_parser("raw", help="Send a raw control/query command")
    raw.add_argument("command", help="Command string (e.g. ?Firmware or !Switch=1,2)")


def run_control(args: argparse.Namespace, options: CliOptions) -> None:
    """Execute a control subcommand."""
    try:
        with control_client(options) as client:
            if args.control_command == "devices":
                emit(client.get_devices(), pretty=options.pretty)
            elif args.control_command == "receivers":
                emit(client.get_receivers(), pretty=options.pretty)
            elif args.control_command == "names":
                emit(client.get_names(tx=args.tx), pretty=options.pretty)
            elif args.control_command == "switch":
                client.switch(args.tx, args.rx)
                emit({"ok": True, "tx": args.tx, "rx": args.rx}, pretty=options.pretty)
            elif args.control_command == "scenes":
                emit(client.get_scenes(), pretty=options.pretty)
            elif args.control_command == "activate-scene":
                client.activate_scene(args.name)
                emit({"ok": True, "scene": args.name}, pretty=options.pretty)
            elif args.control_command == "raw":
                emit_raw(client.send_command(args.command))
    except BaseException as exc:
        handle_error(exc)
