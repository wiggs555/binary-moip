"""CLI output formatting."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from binary_moip.exceptions import ApiError, AuthError, CommandError, ConnectionError, MoIPError


def to_jsonable(value: Any) -> Any:
    """Convert library types to JSON-serializable values."""
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def emit(value: Any, *, pretty: bool = False) -> None:
    """Print a JSON value to stdout."""
    data = to_jsonable(value)
    if pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data))


def emit_raw(text: str) -> None:
    """Print a raw string response (e.g. TCP command reply)."""
    print(text)


def handle_error(exc: BaseException) -> None:
    """Map library exceptions to stderr messages and exit code 1."""
    if isinstance(exc, AuthError):
        print(f"Authentication failed: {exc}", file=sys.stderr)
    elif isinstance(exc, CommandError):
        msg = f"Command failed: {exc}"
        if exc.response:
            msg = f"{msg} ({exc.response})"
        print(msg, file=sys.stderr)
    elif isinstance(exc, ApiError):
        msg = f"API error: {exc}"
        if exc.status_code is not None:
            msg = f"{msg} [HTTP {exc.status_code}]"
        if exc.body:
            msg = f"{msg}\n{exc.body}"
        print(msg, file=sys.stderr)
    elif isinstance(exc, ConnectionError):
        print(f"Connection error: {exc}", file=sys.stderr)
    elif isinstance(exc, MoIPError):
        print(f"Error: {exc}", file=sys.stderr)
    elif isinstance(exc, SystemExit):
        raise
    else:
        print(f"Unexpected error: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc
