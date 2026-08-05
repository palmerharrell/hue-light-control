#!/usr/bin/env python3
"""Discover a Hue Bridge on the local network and pair with it.

Run from backend/ with its venv active:

    python scripts/pair_bridge.py

Finds the bridge via Philips' cloud discovery service (falls back to
--ip if that fails or if you'd rather skip it), prints its hardware
info, then waits for the bridge's physical link button to be pressed
to mint an API key. Writes the resulting bridge_ip/api_key to
config.yaml (gitignored) in the shape backend/app/config.py expects.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import CONFIG_PATH  # noqa: E402

DISCOVERY_URL = "https://discovery.meethue.com/"
DEVICETYPE = "hue-light-control#pairing"
LINK_BUTTON_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 2


def discover_bridge_ip() -> str | None:
    try:
        with urllib.request.urlopen(DISCOVERY_URL, timeout=8) as resp:
            bridges = json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"Cloud discovery failed: {exc}", file=sys.stderr)
        return None
    return bridges[0]["internalipaddress"] if bridges else None


def get_bridge_info(ip: str) -> dict:
    with urllib.request.urlopen(f"http://{ip}/api/config", timeout=5) as resp:
        return json.load(resp)


def request_api_key(ip: str) -> str:
    body = json.dumps({"devicetype": DEVICETYPE}).encode()
    req = urllib.request.Request(
        f"http://{ip}/api",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    print(
        f"Press the link button on the Hue Bridge now "
        f"(waiting up to {LINK_BUTTON_TIMEOUT_SECONDS}s)..."
    )
    deadline = time.monotonic() + LINK_BUTTON_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.load(resp)[0]
        if "success" in result:
            return result["success"]["username"]
        error = result.get("error", {})
        if error.get("type") != 101:  # 101 = link button not pressed
            raise RuntimeError(f"Bridge returned error: {error.get('description', error)}")
        time.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError("Timed out waiting for the link button to be pressed.")


def write_config(ip: str, api_key: str) -> None:
    with CONFIG_PATH.open("w") as f:
        yaml.safe_dump({"bridge_ip": ip, "api_key": api_key}, f)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ip", help="Bridge IP, skips cloud discovery")
    args = parser.parse_args()

    ip = args.ip or discover_bridge_ip()
    if not ip:
        print("Could not discover a bridge. Pass --ip <address> to skip discovery.", file=sys.stderr)
        return 1

    info = get_bridge_info(ip)
    print(f"Found bridge: model {info.get('modelid')}, API {info.get('apiversion')}, sw {info.get('swversion')}")

    try:
        api_key = request_api_key(ip)
    except (RuntimeError, TimeoutError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    write_config(ip, api_key)
    print(f"Wrote bridge_ip and api_key to {CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
