"""Tests for change event parsing."""

from binary_moip.config.events import _parse_raw_event, _parse_ws_payload


def test_parse_raw_event_mod() -> None:
    event = _parse_raw_event("MOD /api/v1/moip/video_rx/1052")
    assert event is not None
    assert event.action == "MOD"
    assert event.path == "/api/v1/moip/video_rx/1052"


def test_parse_ws_payload() -> None:
    event = _parse_ws_payload('{"action":"MOD","url":"/api/v1/moip/unit/1022"}')
    assert event.action == "MOD"
    assert event.path == "/api/v1/moip/unit/1022"
