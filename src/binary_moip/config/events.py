"""Change event subscriptions for MoIP REST API."""

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import socket
import ssl
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
import websockets
from websockets.sync import client as ws_sync

from binary_moip.config.auth import TokenManager
from binary_moip.exceptions import ConnectionError

_RAW_EVENT_RE = re.compile(r"^(ADD|MOD|DEL)\s+(\S+)")


@dataclass(frozen=True, slots=True)
class ChangeEvent:
    """A change notification from the MoIP controller."""

    action: str
    path: str
    raw: str | dict[str, Any]


def _http_to_ws(base_url: str, path: str) -> str:
    parsed = urlparse(base_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    host = parsed.netloc or parsed.path
    return f"{scheme}://{host}{path}"


def _parse_raw_event(line: str) -> ChangeEvent | None:
    stripped = line.strip()
    if not stripped:
        return None
    match = _RAW_EVENT_RE.match(stripped)
    if match:
        return ChangeEvent(action=match.group(1), path=match.group(2), raw=stripped)
    return ChangeEvent(action="PNG", path="", raw=stripped)


def _parse_ws_payload(message: str) -> ChangeEvent:
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return ChangeEvent(action="RAW", path="", raw=message)
    action = str(payload.get("action", payload.get("type", "MOD")))
    path = str(payload.get("url", payload.get("path", "")))
    return ChangeEvent(action=action, path=path, raw=payload)


class AsyncEventClient:
    """Async WebSocket and raw-socket change event subscriptions."""

    def __init__(
        self,
        base_url: str,
        token_manager: TokenManager,
        *,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_manager = token_manager
        self.verify_ssl = verify_ssl

    async def _get_token(self) -> str:
        async with httpx.AsyncClient(base_url=self.base_url, verify=self.verify_ssl) as client:
            return await self.token_manager.aget_token(client)

    async def subscribe_websocket(self) -> AsyncIterator[ChangeEvent]:
        """Subscribe to change events via WebSocket."""
        token = await self._get_token()
        ws_url = _http_to_ws(self.base_url, "/api/v1/moip/change")
        ssl_context = None if self.verify_ssl else ssl._create_unverified_context()
        subprotocol = f"Bearer.{token}"
        async with websockets.connect(
            ws_url,
            subprotocols=[subprotocol],
            ssl=ssl_context,
        ) as websocket:
            async for message in websocket:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                yield _parse_ws_payload(message)

    async def subscribe_raw(self) -> AsyncIterator[ChangeEvent]:
        """Subscribe to change events via raw TCP socket (fallback)."""
        host, port = await self._raw_socket_address()
        reader, writer = await asyncio.open_connection(host, port)
        try:
            buffer = ""
            while True:
                chunk = await reader.read(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    event = _parse_raw_event(line)
                    if event is not None:
                        yield event
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()

    async def _raw_socket_address(self) -> tuple[str, int]:
        async with httpx.AsyncClient(base_url=self.base_url, verify=self.verify_ssl) as client:
            token = await self.token_manager.aget_token(client)
            response = await client.get(
                "/api/v1/moip/raw_change",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            info = response.json()
        parsed = urlparse(self.base_url)
        host = info.get("host") if isinstance(info, dict) else None
        port = info.get("port") if isinstance(info, dict) else None
        if not host:
            host = parsed.hostname or "localhost"
        if not port:
            raise ConnectionError("Could not determine raw change socket port")
        return str(host), int(port)


class SyncEventClient:
    """Synchronous WebSocket and raw-socket change event subscriptions."""

    def __init__(
        self,
        base_url: str,
        token_manager: TokenManager,
        *,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_manager = token_manager
        self.verify_ssl = verify_ssl

    def _get_token(self) -> str:
        with httpx.Client(base_url=self.base_url, verify=self.verify_ssl) as client:
            return self.token_manager.get_token(client)

    def subscribe_websocket(self) -> Iterator[ChangeEvent]:
        """Subscribe to change events via WebSocket."""
        token = self._get_token()
        ws_url = _http_to_ws(self.base_url, "/api/v1/moip/change")
        ssl_context = None if self.verify_ssl else ssl._create_unverified_context()
        subprotocol = f"Bearer.{token}"
        with ws_sync.connect(
            ws_url,
            subprotocols=[subprotocol],
            ssl=ssl_context,
        ) as websocket:
            for message in websocket:
                if isinstance(message, bytes):
                    message = message.decode("utf-8", errors="replace")
                yield _parse_ws_payload(message)

    def subscribe_raw(self) -> Iterator[ChangeEvent]:
        """Subscribe to change events via raw TCP socket (fallback)."""
        host, port = self._raw_socket_address()
        sock = socket.create_connection((host, port))
        try:
            buffer = ""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")
                while "\r\n" in buffer:
                    line, buffer = buffer.split("\r\n", 1)
                    event = _parse_raw_event(line)
                    if event is not None:
                        yield event
        finally:
            sock.close()

    def _raw_socket_address(self) -> tuple[str, int]:
        with httpx.Client(base_url=self.base_url, verify=self.verify_ssl) as client:
            token = self.token_manager.get_token(client)
            response = client.get(
                "/api/v1/moip/raw_change",
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            info = response.json()
        parsed = urlparse(self.base_url)
        host = info.get("host") if isinstance(info, dict) else None
        port = info.get("port") if isinstance(info, dict) else None
        if not host:
            host = parsed.hostname or "localhost"
        if not port:
            raise ConnectionError("Could not determine raw change socket port")
        return str(host), int(port)
