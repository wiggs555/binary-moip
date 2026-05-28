"""JWT authentication for MoIP REST API."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from binary_moip.exceptions import ApiError, AuthError


@dataclass
class TokenData:
    access_token: str
    token_type: str
    expires_at: float


class TokenManager:
    """Acquire and refresh JWT tokens for MoIP REST API access."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        use_digest: bool = True,
        verify_ssl: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.use_digest = use_digest
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self._token: TokenData | None = None
        self._lock = threading.Lock()
        self._async_lock: Any = None

    def _parse_login_response(self, data: dict[str, Any]) -> TokenData:
        try:
            expires_in = int(data.get("expiresIn", 3600))
            return TokenData(
                access_token=str(data["accessToken"]),
                token_type=str(data.get("tokenType", "Bearer")),
                expires_at=time.time() + expires_in - 30,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthError("Invalid login response from controller") from exc

    def _login_sync(self, client: httpx.Client) -> TokenData:
        if self.use_digest:
            response = client.get(
                "/api/v1/base/auth/login",
                auth=httpx.DigestAuth(self.username, self.password),
            )
        else:
            response = client.post(
                "/api/v1/base/auth/login",
                json={"username": self.username, "password": self.password},
            )
        if response.status_code >= 400:
            raise AuthError(
                f"Login failed with status {response.status_code}: {response.text}"
            )
        return self._parse_login_response(response.json())

    async def _login_async(self, client: httpx.AsyncClient) -> TokenData:
        if self.use_digest:
            response = await client.get(
                "/api/v1/base/auth/login",
                auth=httpx.DigestAuth(self.username, self.password),
            )
        else:
            response = await client.post(
                "/api/v1/base/auth/login",
                json={"username": self.username, "password": self.password},
            )
        if response.status_code >= 400:
            raise AuthError(
                f"Login failed with status {response.status_code}: {response.text}"
            )
        return self._parse_login_response(response.json())

    def get_token(self, client: httpx.Client) -> str:
        with self._lock:
            if self._token is None or time.time() >= self._token.expires_at:
                self._token = self._login_sync(client)
            return self._token.access_token

    async def aget_token(self, client: httpx.AsyncClient) -> str:
        if self._async_lock is None:
            import asyncio

            self._async_lock = asyncio.Lock()
        async with self._async_lock:
            if self._token is None or time.time() >= self._token.expires_at:
                self._token = await self._login_async(client)
            return self._token.access_token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None


def raise_for_status(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    raise ApiError(
        f"API request failed: {response.status_code} {response.reason_phrase}",
        status_code=response.status_code,
        body=response.text,
    )
