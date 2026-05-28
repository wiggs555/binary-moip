"""Binary MoIP TCP control protocol v1.9 — command builders and response parsers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Literal

from binary_moip.exceptions import CommandError

COMMAND_TERMINATOR = "\n"


class Resolution(IntEnum):
    """Receiver output resolution modes."""

    PASSTHROUGH = 0
    P1080_60 = 1
    P1080_50 = 2
    P2160_30 = 3
    P2160_25 = 4


class CecMode(IntEnum):
    """HDMI CEC on/off."""

    OFF = 0
    ON = 1


class OsdPosition(IntEnum):
    """On-screen display image position."""

    TOP_RIGHT = 3
    BOTTOM_LEFT = 7
    BOTTOM_RIGHT = 9


class SerialType(IntEnum):
    """Serial port direction: 0 = RX output, 1 = TX input."""

    RX = 0
    TX = 1


class IrType(IntEnum):
    """IR port direction: 0 = RX output, 1 = TX input."""

    RX = 0
    TX = 1


class Parity(str, Enum):
    """Serial parity character."""

    NONE = "n"
    EVEN = "e"
    ODD = "o"


@dataclass(frozen=True, slots=True)
class DeviceCounts:
    tx: int
    rx: int


@dataclass(frozen=True, slots=True)
class ReceiverRouting:
    rx: int
    tx: int


@dataclass(frozen=True, slots=True)
class DeviceName:
    mode: int
    index: int
    name: str


@dataclass(frozen=True, slots=True)
class AudioVolumeLevel:
    rx: int
    level: int


@dataclass(frozen=True, slots=True)
class HdmiAudioMute:
    rx: int
    muted: bool


@dataclass(frozen=True, slots=True)
class SerialMessage:
    port_type: SerialType
    index: int
    data: str


@dataclass(frozen=True, slots=True)
class UnsolicitedReceivers:
    routings: list[ReceiverRouting]


@dataclass(frozen=True, slots=True)
class UnsolicitedAudioVolumeLevels:
    levels: list[int]


UnsolicitedMessage = SerialMessage | UnsolicitedReceivers | UnsolicitedAudioVolumeLevels


def build_query(command: str) -> str:
    """Build a query command without the trailing newline."""
    if command.startswith("?"):
        return command
    return f"?{command}"


def build_control(command: str) -> str:
    """Build a control command without the trailing newline."""
    if command.startswith("!"):
        return command
    return f"!{command}"


def ensure_ok(response: str) -> None:
    """Raise CommandError if the response indicates failure."""
    stripped = response.strip()
    if stripped.startswith("#"):
        raise CommandError(f"Command failed: {stripped}", response=stripped)
    if stripped not in ("OK", "Bye"):
        if stripped.startswith("?"):
            return
        raise CommandError(f"Unexpected response: {stripped}", response=stripped)


def parse_firmware(response: str) -> str:
    """Parse ?Firmware=1.0.0.0 response."""
    match = re.match(r"\?Firmware=(.+)", response.strip())
    if not match:
        raise CommandError(f"Invalid firmware response: {response}", response=response)
    return match.group(1)


def parse_devices(response: str) -> DeviceCounts:
    """Parse ?Devices=1,4 response."""
    match = re.match(r"\?Devices=(\d+),(\d+)", response.strip())
    if not match:
        raise CommandError(f"Invalid devices response: {response}", response=response)
    return DeviceCounts(tx=int(match.group(1)), rx=int(match.group(2)))


def parse_receivers(response: str) -> list[ReceiverRouting]:
    """Parse ?Receivers=1:3,2:0 or ~Receivers=1:3 response."""
    line = response.strip()
    prefix = "?Receivers=" if line.startswith("?Receivers=") else "~Receivers="
    if not line.startswith(prefix):
        raise CommandError(f"Invalid receivers response: {response}", response=response)
    payload = line[len(prefix) :]
    if not payload:
        return []
    routings: list[ReceiverRouting] = []
    for pair in payload.split(","):
        tx_rx = pair.split(":")
        if len(tx_rx) != 2:
            raise CommandError(f"Invalid receiver pair: {pair}", response=response)
        tx, rx = int(tx_rx[0]), int(tx_rx[1])
        routings.append(ReceiverRouting(rx=rx, tx=tx))
    return routings


def parse_names(lines: list[str]) -> list[DeviceName]:
    """Parse multi-line ?Name=MODE,INDEX,NAME responses."""
    names: list[DeviceName] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("?Name="):
            continue
        payload = stripped[len("?Name=") :]
        parts = payload.split(",", 2)
        if len(parts) != 3:
            raise CommandError(f"Invalid name line: {stripped}", response=stripped)
        names.append(
            DeviceName(mode=int(parts[0]), index=int(parts[1]), name=parts[2])
        )
    return names


def parse_scenes(response: str) -> list[str]:
    """Parse ?Scenes={Game Day},{Movie Night} response."""
    line = response.strip()
    if not line.startswith("?Scenes="):
        raise CommandError(f"Invalid scenes response: {response}", response=response)
    payload = line[len("?Scenes=") :]
    if not payload:
        return []
    scenes: list[str] = []
    for match in re.finditer(r"\{([^}]*)\}", payload):
        scenes.append(match.group(1))
    return scenes


def parse_audio_volume_level(response: str) -> AudioVolumeLevel:
    """Parse ?AudioVolumeLevel=1,50 response."""
    match = re.match(r"\?AudioVolumeLevel=(\d+),(\d+)", response.strip(), re.IGNORECASE)
    if not match:
        raise CommandError(f"Invalid audio volume response: {response}", response=response)
    return AudioVolumeLevel(rx=int(match.group(1)), level=int(match.group(2)))


def parse_hdmi_audio_mute(response: str) -> HdmiAudioMute:
    """Parse ?HDMIAudioMute=2,1 response."""
    match = re.match(r"\?HDMIAudioMute=(\d+),(\d+)", response.strip(), re.IGNORECASE)
    if not match:
        raise CommandError(f"Invalid HDMI audio mute response: {response}", response=response)
    return HdmiAudioMute(rx=int(match.group(1)), muted=bool(int(match.group(2))))


def parse_unsolicited(line: str) -> UnsolicitedMessage | None:
    """Parse an unsolicited ~ message line."""
    stripped = line.strip()
    if not stripped.startswith("~"):
        return None

    if stripped.startswith("~Serial="):
        payload = stripped[len("~Serial=") :]
        parts = payload.split(",", 2)
        if len(parts) != 3:
            raise CommandError(f"Invalid serial unsolicited: {stripped}", response=stripped)
        return SerialMessage(
            port_type=SerialType(int(parts[0])),
            index=int(parts[1]),
            data=parts[2],
        )

    if stripped.startswith("~Receivers="):
        return UnsolicitedReceivers(routings=parse_receivers(stripped.replace("~", "?", 1)))

    if stripped.startswith("~AudioVolumeLevels="):
        payload = stripped[len("~AudioVolumeLevels=") :]
        levels = [int(x) for x in payload.split(",") if x]
        return UnsolicitedAudioVolumeLevels(levels=levels)

    return None


def is_response_complete(line: str) -> bool:
    """Return True if a line is a complete command response."""
    stripped = line.strip()
    if not stripped:
        return False
    if stripped in ("OK", "Bye"):
        return True
    if stripped.startswith("#"):
        return True
    if stripped.startswith("?"):
        return True
    if stripped.startswith("~"):
        return False
    return False


def format_receiver_list(rx_ids: list[int]) -> str:
    """Format receiver IDs as [1,2,3] for OSD commands."""
    return "[" + ",".join(str(rx) for rx in rx_ids) + "]"


def format_serial_data(data: bytes | str) -> str:
    """Format serial hex data as space-separated hex bytes."""
    if isinstance(data, str):
        return data
    return " ".join(f"{b:02x}" for b in data)


def build_serial_command(
    port_type: SerialType,
    index: int,
    baud: int,
    data_bits: int,
    parity: str,
    stop_bits: int,
    data: bytes | str,
) -> str:
    """Build !Serial=TYPE,INDEX,BAUD-DATABITS-PARITY-STOPBITS,DATA command."""
    serial_config = f"{baud}-{data_bits}{parity}{stop_bits}"
    hex_data = format_serial_data(data)
    return build_control(f"Serial={port_type.value},{index},{serial_config},{hex_data}")


def build_ir_command(port_type: IrType, index: int, pronto_code: str) -> str:
    """Build !IR=TYPE,INDEX,PRONTOCODE command."""
    return build_control(f"IR={port_type.value},{index},{pronto_code.strip()}")


ResponseKind = Literal["ok", "error", "query", "unsolicited", "unknown"]


def classify_line(line: str) -> ResponseKind:
    """Classify a received line."""
    stripped = line.strip()
    if not stripped:
        return "unknown"
    if stripped.startswith("~"):
        return "unsolicited"
    if stripped.startswith("#"):
        return "error"
    if stripped.startswith("?"):
        return "query"
    if stripped in ("OK", "Bye"):
        return "ok"
    return "unknown"
