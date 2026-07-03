"""Tests for CLI context resolution."""

import os
from unittest.mock import patch

import pytest

from binary_moip.cli.context import resolve_options


def test_resolve_options_from_flags() -> None:
    opts = resolve_options(
        host="192.168.1.10",
        base_url=None,
        user="admin",
        password="secret",
        port=23,
        no_verify_ssl=True,
        timeout=5.0,
        pretty=True,
    )
    assert opts.host == "192.168.1.10"
    assert opts.base_url == "https://192.168.1.10"
    assert opts.username == "admin"
    assert opts.password == "secret"
    assert opts.verify_ssl is False
    assert opts.pretty is True


def test_resolve_options_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOIP_HOST", "10.0.0.5")
    monkeypatch.setenv("MOIP_USER", "envuser")
    monkeypatch.setenv("MOIP_PASS", "envpass")
    monkeypatch.setenv("MOIP_BASE_URL", "https://moip.local")

    opts = resolve_options(
        host=None,
        base_url=None,
        user=None,
        password=None,
        port=23,
        no_verify_ssl=False,
        timeout=10.0,
        pretty=False,
    )
    assert opts.host == "10.0.0.5"
    assert opts.base_url == "https://moip.local"
    assert opts.username == "envuser"
    assert opts.password == "envpass"


def test_resolve_options_missing_host() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        pytest.raises(SystemExit, match="Host is required"),
    ):
        resolve_options(
            host=None,
            base_url=None,
            user="admin",
            password="secret",
            port=23,
            no_verify_ssl=False,
            timeout=10.0,
            pretty=False,
        )


def test_resolve_options_missing_user() -> None:
    with pytest.raises(SystemExit, match="Username is required"):
        resolve_options(
            host="192.168.1.10",
            base_url=None,
            user=None,
            password="secret",
            port=23,
            no_verify_ssl=False,
            timeout=10.0,
            pretty=False,
        )


def test_resolve_options_optional_credentials() -> None:
    """Control commands allow missing credentials without prompting."""
    with patch.dict(os.environ, {}, clear=True):
        opts = resolve_options(
            host="192.168.1.10",
            base_url=None,
            user=None,
            password=None,
            port=23,
            no_verify_ssl=False,
            timeout=10.0,
            pretty=False,
            require_credentials=False,
        )
    assert opts.username == ""
    assert opts.password == ""


def test_resolve_options_optional_credentials_no_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """When credentials are optional, getpass must not be invoked."""

    def _fail_prompt(_prompt: str = "") -> str:
        raise AssertionError("getpass should not be called for optional credentials")

    monkeypatch.setattr("binary_moip.cli.context.getpass", _fail_prompt)
    with patch.dict(os.environ, {}, clear=True):
        opts = resolve_options(
            host="192.168.1.10",
            base_url=None,
            user="admin",
            password=None,
            port=23,
            no_verify_ssl=False,
            timeout=10.0,
            pretty=False,
            require_credentials=False,
        )
    assert opts.username == "admin"
    assert opts.password == ""
