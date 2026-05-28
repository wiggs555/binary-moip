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

See [`examples/`](examples/) for standalone scripts:

- `switch_source.py` — TCP switching
- `list_units.py` — REST unit listing
- `watch_events.py` — async WebSocket listener

## License

MIT — see [LICENSE](LICENSE).
