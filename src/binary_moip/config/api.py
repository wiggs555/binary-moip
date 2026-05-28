"""Dynamic API resource bindings for MoIP REST routes."""

from __future__ import annotations

import re
from typing import Any

from binary_moip.config.routes import ROUTES, Route

_PATH_PARAM_RE = re.compile(r"\{(\w+)\}")


def _route_method_name(route: Route) -> str:
    params = _PATH_PARAM_RE.findall(route.path)
    suffix = route.path.rstrip("/").split("/")[-1]
    list_suffixes = {"unit", "system", "vidwall", "group_rx", "group_tx"}
    if (
        route.method == "get"
        and not params
        and suffix not in ("login", "change", "raw_change")
        and (suffix.endswith("s") or suffix in list_suffixes)
    ):
        return f"list_{suffix}"
    parts = route.path.strip("/").replace("{", "").replace("}", "").split("/")
    name = "_".join(parts[2:])
    return f"{route.method}_{name}"


class ApiNamespace:
    """Namespace exposing one method per REST route under a path prefix."""

    def __init__(
        self,
        transport: Any,
        prefix: str,
        *,
        token_in_query: bool = False,
    ) -> None:
        self._transport = transport
        self._token_in_query = token_in_query
        self._is_async = type(transport).__name__ == "AsyncTransport"
        for route in ROUTES:
            if route.path.startswith(prefix):
                setattr(self, _route_method_name(route), self._make_method(route))

    def _make_method(self, route: Route):
        param_names = _PATH_PARAM_RE.findall(route.path)

        def sync_wrapper(
            *args: Any,
            params: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            auth: bool = True,
            **kwargs: Any,
        ) -> Any:
            path_params = dict(zip(param_names, args, strict=False))
            path_params.update(kwargs)
            return self._transport.request(
                route.method,
                route.path,
                path_params=path_params or None,
                params=params,
                json=json,
                auth=auth,
                token_in_query=self._token_in_query,
            )

        async def async_wrapper(
            *args: Any,
            params: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
            auth: bool = True,
            **kwargs: Any,
        ) -> Any:
            path_params = dict(zip(param_names, args, strict=False))
            path_params.update(kwargs)
            return await self._transport.request(
                route.method,
                route.path,
                path_params=path_params or None,
                params=params,
                json=json,
                auth=auth,
                token_in_query=self._token_in_query,
            )

        wrapper = async_wrapper if self._is_async else sync_wrapper
        wrapper.__name__ = _route_method_name(route)
        wrapper.__doc__ = f"{route.method.upper()} {route.path}"
        return wrapper


class BaseApi(ApiNamespace):
    """Base device API (/api/v1/base/*)."""

    def __init__(self, transport: Any) -> None:
        super().__init__(transport, "/api/v1/base")


class MoipApi(ApiNamespace):
    """MoIP-specific API (/api/v1/moip/*)."""

    def __init__(self, transport: Any) -> None:
        super().__init__(transport, "/api/v1/moip")
