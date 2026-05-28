"""Tests for synchronous ControlClient with mocked socket."""

from __future__ import annotations

import queue
import socket
import threading
import time
from typing import Any

import pytest

from binary_moip.control.client import ControlClient
from binary_moip.exceptions import AuthError, CommandError


class ScriptSocket:
    """Socket mock driven by an auth script plus queued command responses."""

    def __init__(self, auth_chunks: list[bytes]) -> None:
        self._auth = list(auth_chunks)
        self._responses: queue.Queue[bytes] = queue.Queue()
        self.sent: list[bytes] = []
        self._closed = False
        self._lock = threading.Lock()

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)
        payload = data.decode("ascii", errors="replace")
        if payload.startswith("!") or payload.startswith("?"):
            if "Switch=99,99" in payload:
                self._responses.put(b"#Error\n")
            else:
                self._responses.put(b"OK\n")

    def recv(self, size: int) -> bytes:
        with self._lock:
            if self._auth:
                return self._auth.pop(0)
        try:
            return self._responses.get(timeout=1.0)
        except queue.Empty:
            return b""

    def settimeout(self, timeout: float) -> None:
        pass

    def shutdown(self, _how: int) -> None:
        pass

    def close(self) -> None:
        self._closed = True


def test_control_client_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = ScriptSocket([b"login: ", b"password: ", b"Welcome\n"])

    def fake_connect(address: Any, timeout: float = 10.0) -> ScriptSocket:
        return mock

    monkeypatch.setattr(socket, "create_connection", fake_connect)

    client = ControlClient("192.168.1.10", "admin", "secret", timeout=2.0)
    client.connect()
    time.sleep(0.05)
    client.switch(1, 2)
    assert b"!Switch=1,2\n" in mock.sent
    client.close()


def test_control_client_auth_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = ScriptSocket([b"login: ", b"password: ", b"Invalid credentials\nlogin: "])

    def fake_connect(address: Any, timeout: float = 10.0) -> ScriptSocket:
        return mock

    monkeypatch.setattr(socket, "create_connection", fake_connect)

    client = ControlClient("192.168.1.10", "admin", "wrong")
    with pytest.raises(AuthError):
        client.connect()


def test_control_client_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mock = ScriptSocket([b"login: ", b"password: ", b"Welcome\n"])

    def fake_connect(address: Any, timeout: float = 10.0) -> ScriptSocket:
        return mock

    monkeypatch.setattr(socket, "create_connection", fake_connect)

    client = ControlClient("192.168.1.10", "admin", "secret", timeout=2.0)
    client.connect()
    time.sleep(0.05)
    with pytest.raises(CommandError):
        client.send_command("!Switch=99,99")
    client.close()
