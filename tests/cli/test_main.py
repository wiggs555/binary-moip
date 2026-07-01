"""Tests for CLI main dispatch."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from binary_moip.cli.main import main
from binary_moip.control.protocol import DeviceCounts, ReceiverRouting


@pytest.fixture
def mock_control_client() -> MagicMock:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.get_devices.return_value = DeviceCounts(tx=1, rx=4)
    client.get_receivers.return_value = [ReceiverRouting(rx=2, tx=1)]
    client.get_scenes.return_value = ["Movie Night"]
    client.send_command.return_value = "?Firmware=1.0.0.0"
    return client


@pytest.fixture
def mock_config_client() -> MagicMock:
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    client.moip.list_unit.return_value = [{"id": 1}]
    client.moip.list_system.return_value = {"settings": {}}
    client.moip.list_status.return_value = {"status": "ok"}
    client.request.return_value = {"id": 1052}
    return client


def test_control_devices(mock_control_client: MagicMock, capsys) -> None:
    with patch("binary_moip.cli.control.control_client", return_value=mock_control_client):
        main(
            [
                "--host",
                "192.168.1.10",
                "--user",
                "admin",
                "--password",
                "secret",
                "control",
                "devices",
            ]
        )
    mock_control_client.get_devices.assert_called_once()
    out = json.loads(capsys.readouterr().out.strip())
    assert out == {"tx": 1, "rx": 4}


def test_control_switch(mock_control_client: MagicMock, capsys) -> None:
    with patch("binary_moip.cli.control.control_client", return_value=mock_control_client):
        main(
            [
                "--host",
                "192.168.1.10",
                "--user",
                "admin",
                "--password",
                "secret",
                "control",
                "switch",
                "1",
                "2",
            ]
        )
    mock_control_client.switch.assert_called_once_with(1, 2)
    out = json.loads(capsys.readouterr().out.strip())
    assert out["ok"] is True


def test_config_units(mock_config_client: MagicMock, capsys) -> None:
    with patch("binary_moip.cli.config.config_client", return_value=mock_config_client):
        main(
            [
                "--host",
                "192.168.1.10",
                "--user",
                "admin",
                "--password",
                "secret",
                "config",
                "units",
            ]
        )
    mock_config_client.moip.list_unit.assert_called_once()
    out = json.loads(capsys.readouterr().out.strip())
    assert out == [{"id": 1}]


def test_config_request_with_body(mock_config_client: MagicMock, capsys) -> None:
    with patch("binary_moip.cli.config.config_client", return_value=mock_config_client):
        main(
            [
                "--host",
                "192.168.1.10",
                "--user",
                "admin",
                "--password",
                "secret",
                "config",
                "request",
                "PUT",
                "/api/v1/moip/video_rx/1052",
                "--body",
                '{"settings":{"name":"TV"}}',
            ]
        )
    mock_config_client.request.assert_called_once_with(
        "PUT",
        "/api/v1/moip/video_rx/1052",
        params=None,
        json={"settings": {"name": "TV"}},
    )


def test_config_request_with_body_file(mock_config_client: MagicMock, tmp_path, capsys) -> None:
    body_file = tmp_path / "body.json"
    body_file.write_text('{"settings":{"name":"TV"}}', encoding="utf-8")
    with patch("binary_moip.cli.config.config_client", return_value=mock_config_client):
        main(
            [
                "--host",
                "192.168.1.10",
                "--user",
                "admin",
                "--password",
                "secret",
                "config",
                "request",
                "GET",
                "/api/v1/moip/unit",
                "--body-file",
                str(body_file),
            ]
        )
    mock_config_client.request.assert_called_once_with(
        "GET",
        "/api/v1/moip/unit",
        params=None,
        json={"settings": {"name": "TV"}},
    )
