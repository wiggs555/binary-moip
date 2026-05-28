#!/usr/bin/env python3
"""List MoIP units via REST configuration API."""

from binary_moip import ConfigClient

BASE_URL = "https://192.168.1.10"
USERNAME = "admin"
PASSWORD = "secret"


def main() -> None:
    with ConfigClient(BASE_URL, USERNAME, PASSWORD, verify_ssl=False) as client:
        units = client.moip.list_unit()
        for unit in units:
            print(unit)


if __name__ == "__main__":
    main()
