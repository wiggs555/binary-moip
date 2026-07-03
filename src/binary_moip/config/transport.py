"""HTTP transport layer for MoIP REST API."""

from __future__ import annotations

import re
from typing import Any

import httpx

from binary_moip.config.auth import TokenManager, raise_for_status
from binary_moip.exceptions import ApiError

_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


def _ensure_relative_path(path: str) -> None:
    """Reject absolute or protocol-relative paths.

    ``httpx`` treats a fully-qualified or protocol-relative URL as absolute and
    ignores ``base_url``, which would send the bearer token to an arbitrary host.
    Only same-origin paths beginning with a single ``/`` are permitted.
    """
    if "://" in path or path.startswith("//"):
        raise ApiError(f"Refusing request to non-relative path: {path!r}")
    if not path.startswith("/"):
        raise ApiError(f"Request path must be relative and start with '/': {path!r}")


def render_path(path: str, path_params: dict[str, Any] | None) -> str:
    _ensure_relative_path(path)
    if not path_params:
        if "{" in path:
            raise ApiError(f"Missing path parameters for {path}")
        return path

    def replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in path_params:
            raise ApiError(f"Missing path parameter '{key}' for {path}")
        return str(path_params[key])

    return _PATH_PARAM_RE.sub(replacer, path)


class SyncTransport:
    """Synchronous HTTP transport with JWT authentication."""

    def __init__(
        self,
        base_url: str,
        token_manager: TokenManager,
        *,
        verify_ssl: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_manager = token_manager
        self._client = httpx.Client(
            base_url=self.base_url,
            verify=verify_ssl,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> SyncTransport:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def request(
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
        url = render_path(path, path_params)
        headers: dict[str, str] = {}
        query = dict(params or {})
        if auth:
            token = self.token_manager.get_token(self._client)
            if token_in_query:
                query["token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
        response = self._client.request(
            method.upper(), url, params=query or None, json=json, headers=headers
        )
        if response.status_code == 401 and auth:
            self.token_manager.invalidate()
            token = self.token_manager.get_token(self._client)
            if token_in_query:
                query["token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
            response = self._client.request(
                method.upper(), url, params=query or None, json=json, headers=headers
            )
        raise_for_status(response)
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content


class AsyncTransport:
    """Asynchronous HTTP transport with JWT authentication."""

    def __init__(
        self,
        base_url: str,
        token_manager: TokenManager,
        *,
        verify_ssl: bool = True,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_manager = token_manager
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            verify=verify_ssl,
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncTransport:
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

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
        url = render_path(path, path_params)
        headers: dict[str, str] = {}
        query = dict(params or {})
        if auth:
            token = await self.token_manager.aget_token(self._client)
            if token_in_query:
                query["token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
        response = await self._client.request(
            method.upper(), url, params=query or None, json=json, headers=headers
        )
        if response.status_code == 401 and auth:
            self.token_manager.invalidate()
            token = await self.token_manager.aget_token(self._client)
            if token_in_query:
                query["token"] = token
            else:
                headers["Authorization"] = f"Bearer {token}"
            response = await self._client.request(
                method.upper(), url, params=query or None, json=json, headers=headers
            )
        raise_for_status(response)
        if response.status_code == 204 or not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.content
