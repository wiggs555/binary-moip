"""Asynchronous REST configuration client."""

from __future__ import annotations

from typing import Any

from binary_moip.config.api import BaseApi, MoipApi
from binary_moip.config.auth import TokenManager
from binary_moip.config.events import AsyncEventClient
from binary_moip.config.transport import AsyncTransport


class AsyncConfigClient:
    """Asynchronous client for the MoIP REST configuration API (v1.3.0)."""

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
        self._token_manager = TokenManager(
            base_url,
            username,
            password,
            use_digest=use_digest,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        self._transport = AsyncTransport(
            base_url,
            self._token_manager,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
        self.base = BaseApi(self._transport)
        self.moip = MoipApi(self._transport)
        self.events = AsyncEventClient(base_url, self._token_manager, verify_ssl=verify_ssl)

    async def request(
        self,
        method: str,
        path: str,
        *,
        path_params: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        auth: bool = True,
        token_in_query: bool = False,
    ) -> Any:
        """Send an arbitrary authenticated API request."""
        return await self._transport.request(
            method,
            path,
            path_params=path_params,
            params=params,
            json=json,
            auth=auth,
            token_in_query=token_in_query,
        )

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncConfigClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()
