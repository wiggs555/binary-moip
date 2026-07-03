"""Tests for change event parsing."""

import pytest

from binary_moip.config.events import (
    _parse_raw_event,
    _parse_ws_payload,
    _resolve_raw_socket_target,
)
from binary_moip.exceptions import ConnectionError


def test_resolve_raw_socket_target_defaults_to_controller_host() -> None:
    host, port = _resolve_raw_socket_target(
        {"host": "10.0.0.5", "port": 8888},
        "https://10.0.0.5",
        allow_alternate_host=False,
    )
    assert (host, port) == ("10.0.0.5", 8888)


def test_resolve_raw_socket_target_uses_controller_when_host_missing() -> None:
    host, port = _resolve_raw_socket_target(
        {"port": 8888},
        "https://10.0.0.5",
        allow_alternate_host=False,
    )
    assert (host, port) == ("10.0.0.5", 8888)


def test_resolve_raw_socket_target_rejects_alternate_host() -> None:
    with pytest.raises(ConnectionError, match="refusing to connect"):
        _resolve_raw_socket_target(
            {"host": "169.254.169.254", "port": 80},
            "https://10.0.0.5",
            allow_alternate_host=False,
        )


def test_resolve_raw_socket_target_allows_alternate_host_when_opted_in() -> None:
    host, port = _resolve_raw_socket_target(
        {"host": "10.0.0.9", "port": 8888},
        "https://10.0.0.5",
        allow_alternate_host=True,
    )
    assert (host, port) == ("10.0.0.9", 8888)


def test_resolve_raw_socket_target_requires_port() -> None:
    with pytest.raises(ConnectionError, match="port"):
        _resolve_raw_socket_target(
            {"host": "10.0.0.5"},
            "https://10.0.0.5",
            allow_alternate_host=False,
        )


def test_parse_raw_event_mod() -> None:
    event = _parse_raw_event("MOD /api/v1/moip/video_rx/1052")
    assert event is not None
    assert event.action == "MOD"
    assert event.path == "/api/v1/moip/video_rx/1052"


def test_parse_ws_payload() -> None:
    event = _parse_ws_payload('{"action":"MOD","url":"/api/v1/moip/unit/1022"}')
    assert event.action == "MOD"
    assert event.path == "/api/v1/moip/unit/1022"
