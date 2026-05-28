"""Synchronous TCP control client for Binary MoIP port-23 protocol."""

from __future__ import annotations

import contextlib
import socket
import threading
from collections.abc import Callable
from typing import Any

from binary_moip.control import protocol as proto
from binary_moip.control.protocol import (
    AudioVolumeLevel,
    CecMode,
    DeviceCounts,
    DeviceName,
    HdmiAudioMute,
    IrType,
    OsdPosition,
    ReceiverRouting,
    Resolution,
    SerialType,
    UnsolicitedMessage,
    build_control,
    build_ir_command,
    build_query,
    build_serial_command,
    format_receiver_list,
)
from binary_moip.exceptions import AuthError, CommandError, ConnectionError


class ControlClient:
    """Synchronous client for the Binary MoIP TCP control protocol (port 23)."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        port: int = 23,
        timeout: float = 10.0,
        login_prompt: str = "login:",
        password_prompt: str = "password:",
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.login_prompt = login_prompt.lower()
        self.password_prompt = password_prompt.lower()
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()
        self._reader_thread: threading.Thread | None = None
        self._running = False
        self._pending_response: threading.Event | None = None
        self._pending_lines: list[str] = []
        self._unsolicited_callbacks: list[Callable[[UnsolicitedMessage], None]] = []

    def __enter__(self) -> ControlClient:
        self.connect()
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    def connect(self) -> None:
        """Open TCP connection and authenticate."""
        if self._sock is not None:
            return
        try:
            sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            sock.settimeout(self.timeout)
        except OSError as exc:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}") from exc
        self._sock = sock
        self._authenticate()
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def close(self) -> None:
        """Close the TCP connection."""
        self._running = False
        if self._sock is not None:
            with contextlib.suppress(OSError):
                self._sock.shutdown(socket.SHUT_RDWR)
            self._sock.close()
            self._sock = None
        if self._reader_thread is not None:
            self._reader_thread.join(timeout=self.timeout)
            self._reader_thread = None

    def on_unsolicited(self, callback: Callable[[UnsolicitedMessage], None]) -> None:
        """Register a callback for unsolicited ~ messages."""
        self._unsolicited_callbacks.append(callback)

    def send_command(self, command: str) -> str:
        """Send a raw command and return the primary response line."""
        if self._sock is None:
            raise ConnectionError("Not connected")
        with self._lock:
            self._pending_lines = []
            event = threading.Event()
            self._pending_response = event
            try:
                payload = command if command.endswith("\n") else command + "\n"
                self._sock.sendall(payload.encode("ascii"))
                if not event.wait(timeout=self.timeout):
                    raise ConnectionError("Timed out waiting for command response")
                if not self._pending_lines:
                    raise CommandError("Empty response from controller")
                response = self._pending_lines[-1]
                if response.strip().startswith("#"):
                    raise CommandError(
                        f"Command failed: {response.strip()}",
                        response=response.strip(),
                    )
                return response
            finally:
                self._pending_response = None

    def _authenticate(self) -> None:
        if self._sock is None:
            raise ConnectionError("Not connected")
        banner = self._read_until_prompt(self.login_prompt)
        if banner is None:
            raise AuthError("Login prompt not received")
        self._sock.sendall(f"{self.username}\n".encode("ascii"))
        banner = self._read_until_prompt(self.password_prompt)
        if banner is None:
            raise AuthError("Password prompt not received")
        self._sock.sendall(f"{self.password}\n".encode("ascii"))
        response_lines = self._read_lines_until_idle()
        combined = "\n".join(response_lines).lower()
        if "invalid" in combined or "failed" in combined or "denied" in combined:
            raise AuthError("Authentication failed")
        if self.login_prompt in combined:
            raise AuthError("Authentication failed — login prompt repeated")

    def _read_until_prompt(self, prompt: str) -> str | None:
        if self._sock is None:
            return None
        buffer = ""
        while True:
            try:
                chunk = self._sock.recv(4096).decode("ascii", errors="replace")
            except OSError as exc:
                raise ConnectionError("Connection lost during authentication") from exc
            if not chunk:
                return None
            buffer += chunk
            if prompt in buffer.lower():
                return buffer

    def _read_lines_until_idle(self) -> list[str]:
        if self._sock is None:
            return []
        lines: list[str] = []
        self._sock.settimeout(0.5)
        try:
            while True:
                try:
                    chunk = self._sock.recv(4096).decode("ascii", errors="replace")
                except (TimeoutError, OSError):
                    break
                if not chunk:
                    break
                for line in chunk.splitlines():
                    if line.strip():
                        lines.append(line)
        finally:
            self._sock.settimeout(self.timeout)
        return lines

    def _reader_loop(self) -> None:
        buffer = ""
        while self._running and self._sock is not None:
            try:
                chunk = self._sock.recv(4096).decode("ascii", errors="replace")
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                self._handle_line(line)

    def _handle_line(self, line: str) -> None:
        if not line.strip():
            return
        kind = proto.classify_line(line)
        if kind == "unsolicited":
            message = proto.parse_unsolicited(line)
            if message is not None:
                for callback in self._unsolicited_callbacks:
                    callback(message)
            return
        if self._pending_response is not None:
            self._pending_lines.append(line)
            if proto.is_response_complete(line):
                self._pending_response.set()

    def _send_control(self, command: str) -> None:
        response = self.send_command(build_control(command))
        proto.ensure_ok(response)

    # --- Query methods ---

    def get_firmware(self) -> str:
        response = self.send_command(build_query("Firmware"))
        return proto.parse_firmware(response)

    def get_devices(self) -> DeviceCounts:
        response = self.send_command(build_query("Devices"))
        return proto.parse_devices(response)

    def get_receivers(self) -> list[ReceiverRouting]:
        response = self.send_command(build_query("Receivers"))
        return proto.parse_receivers(response)

    def get_names(self, tx: bool) -> list[DeviceName]:
        mode = "1" if tx else "0"
        first = self.send_command(build_query(f"Name={mode}"))
        lines = [first]
        # Additional name lines may arrive as follow-up query lines before OK
        with self._lock:
            extra = [ln for ln in self._pending_lines[:-1] if ln.strip().startswith("?Name=")]
        lines.extend(extra)
        return proto.parse_names(lines)

    def get_scenes(self) -> list[str]:
        response = self.send_command(build_query("Scenes"))
        return proto.parse_scenes(response)

    def get_audio_volume_level(self, rx: int) -> AudioVolumeLevel:
        response = self.send_command(build_query(f"AudioVolumeLevel={rx}"))
        return proto.parse_audio_volume_level(response)

    def get_hdmi_audio_mute(self, rx: int) -> HdmiAudioMute:
        response = self.send_command(build_query(f"HDMIAudioMute={rx}"))
        return proto.parse_hdmi_audio_mute(response)

    # --- Control methods ---

    def switch(self, tx: int, rx: int) -> None:
        self._send_control(f"Switch={tx},{rx}")

    def set_resolution(self, rx: int, resolution: Resolution) -> None:
        self._send_control(f"Resolution={rx},{resolution.value}")

    def set_osd(self, rx: int, message: str) -> None:
        self._send_control(f"OSD={rx},{message}")

    def clear_osd(self, rx: int) -> None:
        self.set_osd(rx, "CLEAR")

    def set_osd_image(
        self,
        url: str,
        refresh_rate: int,
        rx_ids: list[int],
        position: OsdPosition,
    ) -> None:
        receivers = format_receiver_list(rx_ids)
        self._send_control(f"SetOSDImage={url},{refresh_rate},{receivers},{position.value}")

    def set_osd_source(self, tx: int, rx_ids: list[int], position: OsdPosition) -> None:
        receivers = format_receiver_list(rx_ids)
        self._send_control(f"SetOSDSource={tx},{receivers},{position.value}")

    def stop_osd(self, rx_ids: list[int]) -> None:
        receivers = format_receiver_list(rx_ids)
        self._send_control(f"StopOSD={receivers}")

    def reboot(self) -> None:
        self._send_control("Reboot")

    def exit_session(self) -> None:
        response = self.send_command(build_control("Exit"))
        if response.strip() != "Bye":
            proto.ensure_ok(response)

    def set_cec(self, rx: int, mode: CecMode) -> None:
        self._send_control(f"CEC={rx},{mode.value}")

    def send_serial(
        self,
        port_type: SerialType,
        index: int,
        baud: int,
        data_bits: int,
        parity: str,
        stop_bits: int,
        data: bytes | str,
    ) -> None:
        cmd = build_serial_command(
            port_type, index, baud, data_bits, parity, stop_bits, data
        )
        self._send_control(cmd.removeprefix("!"))

    def send_ir(self, port_type: IrType, index: int, pronto_code: str) -> None:
        cmd = build_ir_command(port_type, index, pronto_code)
        self._send_control(cmd.removeprefix("!"))

    def set_audio_volume_level(self, rx: int, level: int) -> None:
        if not 0 <= level <= 100:
            raise ValueError("Volume level must be 0-100")
        self._send_control(f"SetAudioVolumelevel={rx},{level}")

    def set_hdmi_audio_mute(self, rx: int, muted: bool) -> None:
        self._send_control(f"HDMIAudioMute={rx},{1 if muted else 0}")

    def activate_scene(self, name: str) -> None:
        self._send_control(f"ActivateScene={name}")
