#!/usr/bin/env python3
"""Extract OpenAPI 3.0 spec from MoIP Controller API v1.3.0 HTML documentation."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

ENDPOINT_RE = re.compile(r"^(get|post|put|del(?:ete)?)/api/v1/(.+)$", re.IGNORECASE)
AUTH_LINE_RE = re.compile(r"_(BearerAuth|AltJwtAuth|DigestAuth|JwtUrlAuth)_")

METHOD_MAP = {
    "get": "get",
    "post": "post",
    "put": "put",
    "del": "delete",
    "delete": "delete",
}


def normalize_path(raw: str) -> str:
    path = raw.replace("\\_", "_")
    if not path.startswith("/"):
        path = f"/api/v1/{path}"
    return path


def operation_id(method: str, path: str) -> str:
    slug = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    slug = slug.replace("-", "_")
    return f"{method}_{slug}"


def parse_endpoints(lines: list[str]) -> dict[str, dict[str, dict]]:
    paths: dict[str, dict[str, dict]] = {}
    current_auths: set[str] = set()
    pending_body = False

    for line in lines:
        stripped = line.strip()
        auth_match = AUTH_LINE_RE.findall(stripped)
        if auth_match:
            current_auths = set(auth_match)
        if "Request Body schema" in stripped:
            pending_body = True
            continue

        match = ENDPOINT_RE.match(stripped.replace("\\_", "_"))
        if not match:
            continue

        http_method = METHOD_MAP[match.group(1).lower()]
        path = normalize_path(match.group(2))
        op: dict = {
            "operationId": operation_id(http_method, path),
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/GenericObject"}
                        }
                    },
                },
                "400": {"description": "Bad Request"},
                "404": {"description": "Not Found"},
            },
        }
        if current_auths - {"DigestAuth"}:
            op["security"] = [{"BearerAuth": []}]
        if http_method in ("post", "put") and pending_body:
            op["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/GenericObject"}
                    }
                },
            }
        pending_body = False

        paths.setdefault(path, {})[http_method] = op

    return paths


def build_openapi(paths: dict[str, dict[str, dict]]) -> str:
    lines = [
        "openapi: 3.0.3",
        "info:",
        "  title: MoIP Controller API",
        "  version: 1.3.0",
        "  description: REST API for Binary MoIP Controllers",
        "servers:",
        "  - url: http://localhost",
        "    description: Local controller",
        "components:",
        "  securitySchemes:",
        "    BearerAuth:",
        "      type: http",
        "      scheme: bearer",
        "      bearerFormat: JWT",
        "    DigestAuth:",
        "      type: http",
        "      scheme: digest",
        "  schemas:",
        "    GenericObject:",
        "      type: object",
        "      additionalProperties: true",
        "    SuccessResponse:",
        "      type: object",
        "      properties:",
        "        success:",
        "          type: object",
        "          properties:",
        "            code:",
        "              type: integer",
        "            message:",
        "              type: string",
        "    LoginResponse:",
        "      type: object",
        "      properties:",
        "        accessToken:",
        "          type: string",
        "        tokenType:",
        "          type: string",
        "        expiresIn:",
        "          type: integer",
        "paths:",
    ]

    for path in sorted(paths):
        lines.append(f"  {path}:")
        for method, op in sorted(paths[path].items()):
            lines.append(f"    {method}:")
            lines.append(f"      operationId: {op['operationId']}")
            if "security" in op:
                lines.append("      security:")
                lines.append("        - BearerAuth: []")
            if "requestBody" in op:
                lines.append("      requestBody:")
                lines.append("        required: true")
                lines.append("        content:")
                lines.append("          application/json:")
                lines.append("            schema:")
                lines.append("              $ref: '#/components/schemas/GenericObject'")
            lines.append("      responses:")
            for code, response in op["responses"].items():
                lines.append(f"        '{code}':")
                lines.append(f"          description: {response['description']}")

    # Auth endpoints without bearer requirement
    auth_overrides = {
        "/api/v1/base/auth/login": {
            "get": {"security": [{"DigestAuth": []}]},
            "post": {"security": []},
        }
    }
    for path, methods in auth_overrides.items():
        if path in paths:
            for method, override in methods.items():
                if method in paths[path]:
                    if "security" in override:
                        paths[path][method]["security"] = override["security"]
                    elif "security" in paths[path][method]:
                        del paths[path][method]["security"]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default=str(
            Path(__file__).resolve().parents[1]
            / ".cursor"
            / "projects"
            / "Users-andrew-Projects-binary-moip"
            / "uploads"
            / "API_v1.3.0-1.html"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(Path(__file__).resolve().parents[1] / "openapi" / "moip-v1.3.0.yaml"),
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        # Fallback: copy from uploads in cursor projects
        alt = (
            Path.home()
            / ".cursor/projects/Users-andrew-Projects-binary-moip/uploads/API_v1.3.0-1.html"
        )
        if alt.exists():
            input_path = alt
        else:
            raise SystemExit(f"Input file not found: {args.input}")

    lines = input_path.read_text(encoding="utf-8").splitlines()
    paths = parse_endpoints(lines)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(build_openapi(paths), encoding="utf-8")
    print(f"Wrote {len(paths)} paths to {output_path}")


if __name__ == "__main__":
    main()
