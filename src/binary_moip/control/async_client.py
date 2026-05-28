"""Asynchronous TCP control client for Binary MoIP port-23 protocol."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Callable

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


class AsyncControlClient:
    """Asynchronous client for the Binary MoIP TCP control protocol (port 23)."""

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
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._running = False
        self._pending_event: asyncio.Event | None = None
        self._pending_lines: list[str] = []
        self._unsolicited_callbacks: list[Callable[[UnsolicitedMessage], None]] = []

    async def __aenter__(self) -> AsyncControlClient:
        await self.connect()
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.close()

    async def connect(self) -> None:
        """Open TCP connection and authenticate."""
        if self._writer is not None:
            return
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except (OSError, TimeoutError) as exc:
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}") from exc
        await self._authenticate()
        self._running = True
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def close(self) -> None:
        """Close the TCP connection."""
        self._running = False
        if self._reader_task is not None:
            self._reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reader_task
            self._reader_task = None
        if self._writer is not None:
            self._writer.close()
            with contextlib.suppress(OSError):
                await self._writer.wait_closed()
            self._writer = None
            self._reader = None

    def on_unsolicited(self, callback: Callable[[UnsolicitedMessage], None]) -> None:
        """Register a callback for unsolicited ~ messages."""
        self._unsolicited_callbacks.append(callback)

    async def send_command(self, command: str) -> str:
        """Send a raw command and return the primary response line."""
        if self._writer is None or self._reader is None:
            raise ConnectionError("Not connected")
        async with self._lock:
            self._pending_lines = []
            event = asyncio.Event()
            self._pending_event = event
            try:
                payload = command if command.endswith("\n") else command + "\n"
                self._writer.write(payload.encode("ascii"))
                await self._writer.drain()
                try:
                    await asyncio.wait_for(event.wait(), timeout=self.timeout)
                except TimeoutError as exc:
                    raise ConnectionError("Timed out waiting for command response") from exc
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
                self._pending_event = None

    async def _authenticate(self) -> None:
        if self._reader is None or self._writer is None:
            raise ConnectionError("Not connected")
        banner = await self._read_until_prompt(self.login_prompt)
        if banner is None:
            raise AuthError("Login prompt not received")
        self._writer.write(f"{self.username}\n".encode("ascii"))
        await self._writer.drain()
        banner = await self._read_until_prompt(self.password_prompt)
        if banner is None:
            raise AuthError("Password prompt not received")
        self._writer.write(f"{self.password}\n".encode("ascii"))
        await self._writer.drain()
        response_lines = await self._read_lines_until_idle()
        combined = "\n".join(response_lines).lower()
        if "invalid" in combined or "failed" in combined or "denied" in combined:
            raise AuthError("Authentication failed")
        if self.login_prompt in combined:
            raise AuthError("Authentication failed — login prompt repeated")

    async def _read_until_prompt(self, prompt: str) -> str | None:
        if self._reader is None:
            return None
        buffer = ""
        while True:
            try:
                chunk = await asyncio.wait_for(
                    self._reader.read(4096),
                    timeout=self.timeout,
                )
            except TimeoutError:
                return None
            if not chunk:
                return None
            buffer += chunk.decode("ascii", errors="replace")
            if prompt in buffer.lower():
                return buffer

    async def _read_lines_until_idle(self) -> list[str]:
        if self._reader is None:
            return []
        lines: list[str] = []
        while True:
            try:
                chunk = await asyncio.wait_for(self._reader.read(4096), timeout=0.5)
            except TimeoutError:
                break
            if not chunk:
                break
            for line in chunk.decode("ascii", errors="replace").splitlines():
                if line.strip():
                    lines.append(line)
        return lines

    async def _reader_loop(self) -> None:
        if self._reader is None:
            return
        buffer = ""
        while self._running:
            try:
                chunk = await self._reader.read(4096)
            except (OSError, asyncio.CancelledError):
                break
            if not chunk:
                break
            buffer += chunk.decode("ascii", errors="replace")
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
        if self._pending_event is not None:
            self._pending_lines.append(line)
            if proto.is_response_complete(line):
                self._pending_event.set()

    async def _send_control(self, command: str) -> None:
        response = await self.send_command(build_control(command))
        proto.ensure_ok(response)

    async def get_firmware(self) -> str:
        response = await self.send_command(build_query("Firmware"))
        return proto.parse_firmware(response)

    async def get_devices(self) -> DeviceCounts:
        response = await self.send_command(build_query("Devices"))
        return proto.parse_devices(response)

    async def get_receivers(self) -> list[ReceiverRouting]:
        response = await self.send_command(build_query("Receivers"))
        return proto.parse_receivers(response)

    async def get_names(self, tx: bool) -> list[DeviceName]:
        mode = "1" if tx else "0"
        first = await self.send_command(build_query(f"Name={mode}"))
        lines = [first]
        extra = [ln for ln in self._pending_lines[:-1] if ln.strip().startswith("?Name=")]
        lines.extend(extra)
        return proto.parse_names(lines)

    async def get_scenes(self) -> list[str]:
        response = await self.send_command(build_query("Scenes"))
        return proto.parse_scenes(response)

    async def get_audio_volume_level(self, rx: int) -> AudioVolumeLevel:
        response = await self.send_command(build_query(f"AudioVolumeLevel={rx}"))
        return proto.parse_audio_volume_level(response)

    async def get_hdmi_audio_mute(self, rx: int) -> HdmiAudioMute:
        response = await self.send_command(build_query(f"HDMIAudioMute={rx}"))
        return proto.parse_hdmi_audio_mute(response)

    async def switch(self, tx: int, rx: int) -> None:
        await self._send_control(f"Switch={tx},{rx}")

    async def set_resolution(self, rx: int, resolution: Resolution) -> None:
        await self._send_control(f"Resolution={rx},{resolution.value}")

    async def set_osd(self, rx: int, message: str) -> None:
        await self._send_control(f"OSD={rx},{message}")

    async def clear_osd(self, rx: int) -> None:
        await self.set_osd(rx, "CLEAR")

    async def set_osd_image(
        self,
        url: str,
        refresh_rate: int,
        rx_ids: list[int],
        position: OsdPosition,
    ) -> None:
        receivers = format_receiver_list(rx_ids)
        await self._send_control(
            f"SetOSDImage={url},{refresh_rate},{receivers},{position.value}"
        )

    async def set_osd_source(self, tx: int, rx_ids: list[int], position: OsdPosition) -> None:
        receivers = format_receiver_list(rx_ids)
        await self._send_control(f"SetOSDSource={tx},{receivers},{position.value}")

    async def stop_osd(self, rx_ids: list[int]) -> None:
        receivers = format_receiver_list(rx_ids)
        await self._send_control(f"StopOSD={receivers}")

    async def reboot(self) -> None:
        await self._send_control("Reboot")

    async def exit_session(self) -> None:
        response = await self.send_command(build_control("Exit"))
        if response.strip() != "Bye":
            proto.ensure_ok(response)

    async def set_cec(self, rx: int, mode: CecMode) -> None:
        await self._send_control(f"CEC={rx},{mode.value}")

    async def send_serial(
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
        await self._send_control(cmd.removeprefix("!"))

    async def send_ir(self, port_type: IrType, index: int, pronto_code: str) -> None:
        cmd = build_ir_command(port_type, index, pronto_code)
        await self._send_control(cmd.removeprefix("!"))

    async def set_audio_volume_level(self, rx: int, level: int) -> None:
        if not 0 <= level <= 100:
            raise ValueError("Volume level must be 0-100")
        await self._send_control(f"SetAudioVolumelevel={rx},{level}")

    async def set_hdmi_audio_mute(self, rx: int, muted: bool) -> None:
        await self._send_control(f"HDMIAudioMute={rx},{1 if muted else 0}")

    async def activate_scene(self, name: str) -> None:
        await self._send_control(f"ActivateScene={name}")
