#!/usr/bin/env python3
"""Generate config/routes.py from MoIP API HTML documentation."""

from __future__ import annotations

import re
from pathlib import Path

ENDPOINT_RE = re.compile(r"^(get|post|put|del(?:ete)?)/api/v1/(.+)$", re.IGNORECASE)

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "API_v1.3.0.html"
OUTPUT = ROOT / "src" / "binary_moip" / "config" / "routes.py"


def normalize_path(raw: str) -> str:
    return "/api/v1/" + raw.replace("\\_", "_")


def to_method_name(http_method: str, path: str) -> str:
    parts = path.strip("/").split("/")
    slug = "_".join(p.replace("{", "").replace("}", "") for p in parts[2:])
    if http_method == "get" and not path.endswith("}") and (
        slug.endswith("s") or slug in ("unit", "system", "vidwall")
    ):
        return f"list_{slug.replace('/', '_')}" if "/" in slug else f"list_{slug}"
    return f"{http_method}_{slug.replace('/', '_')}"


def main() -> None:
    lines = HTML.read_text(encoding="utf-8").splitlines()
    endpoints: list[tuple[str, str, bool]] = []
    pending_body = False
    seen: set[tuple[str, str]] = set()

    for line in lines:
        stripped = line.strip()
        if "Request Body schema" in stripped:
            pending_body = True
            continue
        match = ENDPOINT_RE.match(stripped.replace("\\_", "_"))
        if not match:
            continue
        method = match.group(1).lower()
        if method == "del":
            method = "delete"
        path = normalize_path(match.group(2))
        key = (method, path)
        if key in seen:
            continue
        seen.add(key)
        has_body = pending_body and method in ("post", "put")
        endpoints.append((method, path, has_body))
        pending_body = False

    out: list[str] = [
        '"""Auto-generated route registry for MoIP REST API v1.3.0."""',
        "",
        "from __future__ import annotations",
        "",
        "from dataclasses import dataclass",
        "",
        "",
        "@dataclass(frozen=True, slots=True)",
        "class Route:",
        '    """HTTP route definition."""',
        "",
        "    method: str",
        "    path: str",
        "    has_body: bool = False",
        "",
        "",
        "ROUTES: tuple[Route, ...] = (",
    ]
    for method, path, has_body in sorted(endpoints, key=lambda x: (x[1], x[0])):
        out.append(f'    Route("{method}", "{path}", {has_body}),')
    out.append(")")
    out.append("")

    OUTPUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(endpoints)} routes to {OUTPUT}")


if __name__ == "__main__":
    main()
