#!/usr/bin/env python3
"""Watch MoIP change events via WebSocket."""

import asyncio

from binary_moip import AsyncConfigClient

BASE_URL = "https://192.168.1.10"
USERNAME = "admin"
PASSWORD = "secret"


async def main() -> None:
    async with AsyncConfigClient(BASE_URL, USERNAME, PASSWORD, verify_ssl=False) as client:
        async for event in client.events.subscribe_websocket():
            print(f"{event.action} {event.path}")


if __name__ == "__main__":
    asyncio.run(main())
