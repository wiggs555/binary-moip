"""Tests for route registry completeness."""

from binary_moip.config.routes import ROUTES


def test_route_count() -> None:
    assert len(ROUTES) == 83


def test_all_routes_have_method_and_path() -> None:
    for route in ROUTES:
        assert route.method in {"get", "post", "put", "delete"}
        assert route.path.startswith("/api/v1/")
