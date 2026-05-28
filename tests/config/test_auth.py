"""Tests for REST API authentication and transport."""

from __future__ import annotations

import httpx
import pytest
import respx

from binary_moip.config.auth import TokenManager
from binary_moip.config.client import ConfigClient
from binary_moip.config.transport import SyncTransport
from binary_moip.exceptions import AuthError


@respx.mock
def test_token_manager_post_login() -> None:
    respx.post("http://controller/api/v1/base/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "accessToken": "test-token",
                "tokenType": "Bearer",
                "expiresIn": 3600,
            },
        )
    )
    manager = TokenManager(
        "http://controller",
        "admin",
        "secret",
        use_digest=False,
    )
    with httpx.Client(base_url="http://controller") as client:
        token = manager.get_token(client)
    assert token == "test-token"


@respx.mock
def test_token_manager_digest_login() -> None:
    route = respx.get("http://controller/api/v1/base/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={
                "accessToken": "digest-token",
                "tokenType": "Bearer",
                "expiresIn": 3600,
            },
        )
    )
    manager = TokenManager("http://controller", "admin", "secret", use_digest=True)
    with httpx.Client(base_url="http://controller") as client:
        token = manager.get_token(client)
    assert token == "digest-token"
    assert route.called


@respx.mock
def test_token_manager_login_failure() -> None:
    respx.post("http://controller/api/v1/base/auth/login").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    manager = TokenManager("http://controller", "admin", "bad", use_digest=False)
    with httpx.Client(base_url="http://controller") as client, pytest.raises(AuthError):
        manager.get_token(client)


@respx.mock
def test_config_client_list_units() -> None:
    respx.post("http://controller/api/v1/base/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={"accessToken": "tok", "tokenType": "Bearer", "expiresIn": 3600},
        )
    )
    respx.get("http://controller/api/v1/moip/unit").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "label": "TX-1"}])
    )
    with ConfigClient("http://controller", "admin", "secret", use_digest=False) as client:
        units = client.moip.list_unit()
    assert units == [{"id": 1, "label": "TX-1"}]


@respx.mock
def test_transport_path_params() -> None:
    respx.post("http://controller/api/v1/base/auth/login").mock(
        return_value=httpx.Response(
            200,
            json={"accessToken": "tok", "tokenType": "Bearer", "expiresIn": 3600},
        )
    )
    route = respx.get("http://controller/api/v1/moip/video_rx/1052").mock(
        return_value=httpx.Response(200, json={"id": 1052})
    )
    manager = TokenManager("http://controller", "admin", "secret", use_digest=False)
    with SyncTransport("http://controller", manager) as transport:
        result = transport.request("GET", "/api/v1/moip/video_rx/{id}", path_params={"id": 1052})
    assert result == {"id": 1052}
    assert route.called
