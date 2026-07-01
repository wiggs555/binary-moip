"""Tests for CLI output serialization."""

import json

from binary_moip.cli.output import emit, to_jsonable
from binary_moip.control.protocol import DeviceCounts, DeviceName, ReceiverRouting


def test_to_jsonable_dataclass() -> None:
    counts = DeviceCounts(tx=2, rx=5)
    assert to_jsonable(counts) == {"tx": 2, "rx": 5}


def test_to_jsonable_list() -> None:
    routings = [ReceiverRouting(rx=3, tx=1)]
    assert to_jsonable(routings) == [{"rx": 3, "tx": 1}]


def test_to_jsonable_device_name() -> None:
    name = DeviceName(mode=0, index=1, name="Basement TV")
    assert to_jsonable(name) == {"mode": 0, "index": 1, "name": "Basement TV"}


def test_emit_compact(capsys) -> None:
    emit({"ok": True}, pretty=False)
    captured = capsys.readouterr()
    assert captured.out.strip() == json.dumps({"ok": True})


def test_emit_pretty(capsys) -> None:
    emit({"ok": True}, pretty=True)
    captured = capsys.readouterr()
    assert '"ok": true' in captured.out
