#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 scripts/extract_openapi.py docs/API_v1.3.0.html -o openapi/moip-v1.3.0.yaml

rm -rf src/binary_moip/generated/moip_client
"$(dirname "$0")/../.venv/bin/openapi-python-client" generate \
  --path openapi/moip-v1.3.0.yaml \
  --output-path src/binary_moip/generated/moip_client \
  --config scripts/openapi-config.yaml \
  --meta none

echo "Generated client at src/binary_moip/generated/moip_client"
