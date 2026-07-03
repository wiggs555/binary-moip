"""Tests for REST transport path handling."""

import pytest

from binary_moip.config.transport import render_path
from binary_moip.exceptions import ApiError


def test_render_path_relative_ok() -> None:
    assert render_path("/api/v1/moip/unit", None) == "/api/v1/moip/unit"


def test_render_path_substitutes_params() -> None:
    result = render_path("/api/v1/moip/video_rx/{id}", {"id": 1052})
    assert result == "/api/v1/moip/video_rx/1052"


@pytest.mark.parametrize(
    "path",
    [
        "https://attacker.example/collect",
        "http://attacker.example/",
        "//attacker.example/steal",
        "ftp://attacker.example/x",
    ],
)
def test_render_path_rejects_absolute_urls(path: str) -> None:
    with pytest.raises(ApiError):
        render_path(path, None)


def test_render_path_rejects_non_slash_relative() -> None:
    with pytest.raises(ApiError, match="must be relative"):
        render_path("api/v1/moip/unit", None)


def test_render_path_missing_param() -> None:
    with pytest.raises(ApiError, match="Missing path parameter"):
        render_path("/api/v1/moip/video_rx/{id}", {"other": 1})
