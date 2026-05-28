#!/usr/bin/env python3
"""Switch a receiver to a transmitter via TCP control API."""

from binary_moip import ControlClient

HOST = "192.168.1.10"
USERNAME = "admin"
PASSWORD = "secret"
TX = 1
RX = 2


def main() -> None:
    with ControlClient(HOST, USERNAME, PASSWORD) as client:
        print(f"Devices: {client.get_devices()}")
        print(f"Routing before: {client.get_receivers()}")
        client.switch(TX, RX)
        print(f"Switched RX {RX} to TX {TX}")


if __name__ == "__main__":
    main()
