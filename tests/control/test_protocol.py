"""Tests for TCP control protocol parsing."""

import pytest

from binary_moip.control import protocol as proto
from binary_moip.control.protocol import (
    CecMode,
    Resolution,
    build_control,
    build_query,
    build_serial_command,
    format_receiver_list,
)
from binary_moip.exceptions import CommandError


def test_build_query_and_control() -> None:
    assert build_query("Firmware") == "?Firmware"
    assert build_control("Switch=1,2") == "!Switch=1,2"


def test_parse_firmware() -> None:
    assert proto.parse_firmware("?Firmware=3.0.4.8") == "3.0.4.8"


def test_parse_devices() -> None:
    counts = proto.parse_devices("?Devices=2,5")
    assert counts.tx == 2
    assert counts.rx == 5


def test_parse_receivers() -> None:
    routings = proto.parse_receivers("?Receivers=1:3,2:0")
    assert len(routings) == 2
    assert routings[0].tx == 1 and routings[0].rx == 3
    assert routings[1].tx == 2 and routings[1].rx == 0


def test_parse_names() -> None:
    names = proto.parse_names(
        [
            "?Name=0,1,RX-D46A91210620",
            "?Name=0,2,Basement TV",
        ]
    )
    assert len(names) == 2
    assert names[1].name == "Basement TV"


def test_parse_scenes() -> None:
    scenes = proto.parse_scenes("?Scenes={Game Day},{Movie Night}")
    assert scenes == ["Game Day", "Movie Night"]


def test_parse_unsolicited_serial() -> None:
    msg = proto.parse_unsolicited("~Serial=1,2,61 62 63")
    assert msg is not None
    assert msg.index == 2
    assert msg.data == "61 62 63"


def test_ensure_ok_raises_on_error() -> None:
    with pytest.raises(CommandError):
        proto.ensure_ok("#Error")


def test_format_receiver_list() -> None:
    assert format_receiver_list([1, 2, 3]) == "[1,2,3]"


def test_build_serial_command() -> None:
    cmd = build_serial_command(
        proto.SerialType.TX, 2, 9600, 8, "n", 1, b"abc"
    )
    assert cmd == "!Serial=1,2,9600-8n1,61 62 63"


def test_resolution_enum() -> None:
    assert Resolution.PASSTHROUGH == 0
    assert CecMode.OFF == 0
