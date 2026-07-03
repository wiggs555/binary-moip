# binary-moip

Python wrapper for the SnapAV Binary MoIP controller APIs:

- **Control API** — TCP port 23, ASCII command protocol ([v1.9 spec](https://www.snapav.com/wcsstore/ExtendedSitesCatalogAssetStore/attachments/documents/MediaDistribution/ProtocolsAndDrivers/SnapAV_Binary_MoIP_API_V1.9.pdf))
- **Configuration API** — HTTPS REST + WebSocket events ([v1.3.0 spec](https://help.snapone.com/moip-ig/Content/Binary%20MoIP%20Topics/API%20v1.3.0.html))

## Firmware compatibility

| API | Typical firmware | Notes |
|-----|------------------|-------|
| TCP control (port 23) | ≤ 3.x | Legacy integration protocol |
| REST configuration | ≥ 4.x | JWT auth, full device management |

Many current deployments use REST only. Both clients are included for backward compatibility.

## Installation

```bash
pip install binary-moip
```

Development install:

```bash
git clone https://github.com/binary-moip/binary-moip
cd binary-moip
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Command-line interface

After installation, the `binary-moip` command is available on your PATH (also runnable as `python -m binary_moip.cli`).

### Connection options

Global flags apply to all subcommands:

| Flag | Environment variable | Description |
|------|---------------------|-------------|
| `--host` | `MOIP_HOST` | Controller hostname or IP |
| `--base-url` | `MOIP_BASE_URL` | REST base URL (default: `https://{host}`) |
| `--user` | `MOIP_USER` | Username (optional for `control` commands) |
| `--password` | `MOIP_PASS` | Password (prompted if unset for `config` commands) |
| `--port` | — | TCP control port (default: 23) |
| `--no-verify-ssl` | — | Disable SSL verification for REST |
| `--pretty` | — | Pretty-print JSON output |

### TCP control examples

The `control` commands use the TCP control connection (port 23). Authentication is
optional and auto-detected: if the controller presents a login prompt the supplied
`--user`/`--password` are used, otherwise you can omit them entirely.

```bash
# No credentials needed when the controller does not require authentication
binary-moip --host 192.168.1.10 control devices

binary-moip --host 192.168.1.10 --user admin --password secret control devices
binary-moip --host 192.168.1.10 --user admin --password secret control receivers
binary-moip --host 192.168.1.10 --user admin --password secret control names --rx
binary-moip --host 192.168.1.10 --user admin --password secret control switch 1 2
binary-moip --host 192.168.1.10 --user admin --password secret control scenes
binary-moip --host 192.168.1.10 --user admin --password secret control activate-scene "Good Night"
binary-moip --host 192.168.1.10 --user admin --password secret control raw "?Firmware"
```

### REST configuration examples

```bash
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl config units
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl config system
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl config status
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl \
  config request GET /api/v1/moip/video_rx/1052
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl \
  config request PUT /api/v1/moip/video_rx/1052 --body '{"settings":{"name":"TV"}}'
binary-moip --host 192.168.1.10 --user admin --password secret --no-verify-ssl config watch
```

The `config request` subcommand provides access to all REST API endpoints. Use `config watch` to stream change events (Ctrl+C to stop).

## Quick start — TCP control

Switch receiver 2 to transmitter 1:

```python
from binary_moip import ControlClient

with ControlClient("192.168.1.10", username="admin", password="secret") as client:
    print(client.get_devices())       # DeviceCounts(tx=2, rx=5)
    print(client.get_receivers())     # current routing
    client.switch(tx=1, rx=2)         # !Switch=1,2
```

Async:

```python
from binary_moip import AsyncControlClient

async with AsyncControlClient("192.168.1.10", "admin", "secret") as client:
    await client.switch(1, 2)
```

Authentication is optional and auto-detected. On connect, if the controller
presents a login prompt the supplied credentials are used; otherwise the session
is treated as ready and commands are sent immediately. Controllers that do not
require authentication can be used without credentials:

```python
with ControlClient("192.168.1.10") as client:
    client.switch(tx=1, rx=2)
```

## Quick start — REST configuration

List units and read video RX settings:

```python
from binary_moip import ConfigClient

with ConfigClient("https://192.168.1.10", "admin", "secret", verify_ssl=False) as client:
    units = client.moip.list_unit()
    video_rx = client.moip.get_video_rx_id(1052, id=1052)
```

Async:

```python
from binary_moip import AsyncConfigClient

async with AsyncConfigClient("https://192.168.1.10", "admin", "secret", verify_ssl=False) as client:
    units = await client.moip.list_unit()
```

## Event subscription

Subscribe to configuration changes via WebSocket:

```python
from binary_moip import AsyncConfigClient

async with AsyncConfigClient("https://192.168.1.10", "admin", "secret", verify_ssl=False) as client:
    async for event in client.events.subscribe_websocket():
        print(event.action, event.path)
```

## API surface

### Control client methods

Query: `get_firmware`, `get_devices`, `get_receivers`, `get_names`, `get_scenes`, `get_audio_volume_level`, `get_hdmi_audio_mute`

Control: `switch`, `set_resolution`, `set_osd`, `clear_osd`, `set_osd_image`, `set_osd_source`, `stop_osd`, `set_cec`, `send_serial`, `send_ir`, `set_audio_volume_level`, `set_hdmi_audio_mute`, `activate_scene`, `reboot`, `exit_session`

Callbacks: `on_unsolicited(callback)` for `~Serial`, `~Receivers`, and `~AudioVolumeLevels` messages.

### REST client namespaces

- `client.base` — `/api/v1/base/*` (auth, config, LAN, firmware, info)
- `client.moip` — `/api/v1/moip/*` (units, endpoints, video walls, groups)
- `client.events` — WebSocket and raw change socket subscriptions
- `client.request(method, path, ...)` — arbitrary authenticated requests

All 83 REST routes from API v1.3.0 are exposed as methods on `client.base` and `client.moip`. Method names follow the pattern `list_unit`, `get_video_rx_id`, `put_video_rx_id`, etc.

## Development

```bash
# Regenerate OpenAPI spec from HTML docs
python scripts/extract_openapi.py docs/API_v1.3.0.html

# Regenerate route registry
python scripts/generate_routes.py

# Run tests
pytest

# Lint
ruff check src tests
```

## Examples

See [`examples/`](examples/) for standalone scripts (or use the CLI equivalents above):

- `switch_source.py` — TCP switching (`binary-moip control switch`)
- `list_units.py` — REST unit listing (`binary-moip config units`)
- `watch_events.py` — WebSocket listener (`binary-moip config watch`)

## License

MIT — see [LICENSE](LICENSE).
