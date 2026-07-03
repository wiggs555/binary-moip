"""CLI connection context — resolve credentials from flags and environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from getpass import getpass

from binary_moip.config.client import ConfigClient
from binary_moip.control.client import ControlClient


@dataclass(frozen=True, slots=True)
class CliOptions:
    """Resolved CLI connection options."""

    host: str
    base_url: str
    username: str
    password: str
    port: int
    verify_ssl: bool
    timeout: float
    pretty: bool


def resolve_options(
    *,
    host: str | None,
    base_url: str | None,
    user: str | None,
    password: str | None,
    port: int,
    no_verify_ssl: bool,
    timeout: float,
    pretty: bool,
    require_credentials: bool = True,
) -> CliOptions:
    """Resolve connection options from CLI flags and environment variables.

    When ``require_credentials`` is False (e.g. for the TCP ``control`` commands,
    where the controller may not require authentication), a missing username is
    allowed and the password is not prompted for; both default to empty strings.
    """
    resolved_host = host or os.environ.get("MOIP_HOST")
    if not resolved_host:
        raise SystemExit("Host is required (--host or MOIP_HOST)")

    resolved_base_url = base_url or os.environ.get("MOIP_BASE_URL") or f"https://{resolved_host}"

    resolved_user = user or os.environ.get("MOIP_USER")
    resolved_password = password or os.environ.get("MOIP_PASS")

    if require_credentials:
        if not resolved_user:
            raise SystemExit("Username is required (--user or MOIP_USER)")
        if not resolved_password:
            resolved_password = getpass("Password: ")
    else:
        resolved_user = resolved_user or ""
        resolved_password = resolved_password or ""

    return CliOptions(
        host=resolved_host,
        base_url=resolved_base_url.rstrip("/"),
        username=resolved_user,
        password=resolved_password,
        port=port,
        verify_ssl=not no_verify_ssl,
        timeout=timeout,
        pretty=pretty,
    )


def control_client(options: CliOptions) -> ControlClient:
    """Build a ControlClient from resolved options."""
    return ControlClient(
        options.host,
        options.username,
        options.password,
        port=options.port,
        timeout=options.timeout,
    )


def config_client(options: CliOptions) -> ConfigClient:
    """Build a ConfigClient from resolved options."""
    return ConfigClient(
        options.base_url,
        options.username,
        options.password,
        verify_ssl=options.verify_ssl,
        timeout=options.timeout,
    )
