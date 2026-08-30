import asyncio
import ipaddress
import logging
import socket
import time
from typing import Optional

import httpx

from app.config import BridgeConfig, load_config, update_bridge_ip

logger = logging.getLogger(__name__)

# Serializes rediscovery so concurrent callers (e.g. the frontend's proactive
# health check racing a panel's own failed request) don't each run their own
# SSDP/cloud search and race to write config.yaml.
_rediscovery_lock = asyncio.Lock()

CLOUD_DISCOVERY_URL = "https://discovery.meethue.com/"

_SSDP_ADDR = "239.255.255.250"
_SSDP_PORT = 1900
_SSDP_MX = 3
_SSDP_SEARCH_TARGET = "urn:schemas-upnp-org:device:basic:1"
_SSDP_MESSAGE = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {_SSDP_ADDR}:{_SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    f"MX: {_SSDP_MX}\r\n"
    f"ST: {_SSDP_SEARCH_TARGET}\r\n"
    "\r\n"
).encode()

# After a fully-failed rediscovery, skip retrying for this long so a
# genuinely offline bridge doesn't turn every request into a long hang.
_FAILURE_COOLDOWN_SECONDS = 60.0
_last_failure_at: Optional[float] = None


def _ssdp_search(timeout: float) -> Optional[str]:
    """Send an SSDP M-SEARCH and return the first Hue bridge IP that replies.

    Hue bridges identify themselves in the M-SEARCH response body with an
    "IpBridge" server string. This is blocking socket I/O — call it via an
    executor from async code. The candidate is confirmed against our own
    api_key by _verify_bridge before being trusted, since any host that sees
    the multicast query could in principle reply.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.sendto(_SSDP_MESSAGE, (_SSDP_ADDR, _SSDP_PORT))
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                data, (ip, _port) = sock.recvfrom(2048)
            except socket.timeout:
                break
            if b"IpBridge" in data:
                return ip
    except OSError as exc:
        logger.warning("SSDP discovery failed: %s", exc)
    finally:
        sock.close()
    return None


async def discover_local(timeout: float = 5.0) -> Optional[str]:
    """Find a bridge on the local network via SSDP multicast. Works with no
    internet access — LAN multicast only.

    Note: multicast may not reach the LAN from inside a container on
    Docker's default bridge network; that needs --network host or macvlan.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _ssdp_search, timeout)


def _is_private_address(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


async def discover_cloud(timeout: float = 5.0) -> Optional[str]:
    """Find a bridge via Philips' cloud discovery service. Requires internet
    access, so this is only worth trying when local discovery fails."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(CLOUD_DISCOVERY_URL)
            resp.raise_for_status()
            bridges = resp.json()
        candidate = bridges[0]["internalipaddress"] if bridges else None
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Cloud discovery failed: %s", exc)
        return None

    if candidate is not None and not _is_private_address(candidate):
        # Don't send our api_key to whatever this is.
        logger.warning("Cloud discovery returned a non-private address, ignoring")
        return None
    return candidate


async def _verify_bridge(ip: str, api_key: str, timeout: float = 5.0) -> bool:
    """Confirm a candidate IP is actually our paired bridge (not a neighbor's
    or an unrelated host) by checking it accepts our api_key.

    The bridge always answers HTTP 200, even for a bad api_key — the actual
    result is conveyed as a JSON error-list body, so raise_for_status()
    alone can't distinguish "our bridge" from "any Hue bridge".
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"http://{ip}/api/{api_key}/config")
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return False
    return not isinstance(data, list)


async def rediscover_bridge_ip(api_key: str) -> Optional[str]:
    """Find the bridge's current IP, local discovery first so this works
    offline, falling back to cloud discovery only if that fails."""
    global _last_failure_at
    if (
        _last_failure_at is not None
        and time.monotonic() - _last_failure_at < _FAILURE_COOLDOWN_SECONDS
    ):
        return None

    for discover in (discover_local, discover_cloud):
        candidate = await discover()
        if candidate and await _verify_bridge(candidate, api_key):
            _last_failure_at = None
            return candidate

    _last_failure_at = time.monotonic()
    return None


async def ensure_bridge_reachable(config: BridgeConfig) -> dict:
    """Proactively verify the configured bridge_ip is still valid, repairing
    config.yaml via rediscovery if it isn't. Meant to be called once on page
    load (via /api/health) so a drifted IP self-heals before the frontend's
    panels fire their own requests, rather than only reacting to a failure.

    Never raises — a health endpoint needs a clean status even when the
    bridge is genuinely unreachable.
    """
    if not config.bridge_ip or not config.api_key:
        return {"reachable": False, "configured": False, "bridge_ip": None}

    if await _verify_bridge(config.bridge_ip, config.api_key):
        return {"reachable": True, "configured": True, "bridge_ip": config.bridge_ip}

    async with _rediscovery_lock:
        # A concurrent caller (e.g. a panel's own failed request) may have
        # already repaired config.yaml while we were waiting for the lock.
        current = load_config()
        if current.bridge_ip and current.bridge_ip != config.bridge_ip:
            if await _verify_bridge(current.bridge_ip, current.api_key):
                return {"reachable": True, "configured": True, "bridge_ip": current.bridge_ip}

        new_ip = await rediscover_bridge_ip(config.api_key)
        if new_ip is None:
            return {"reachable": False, "configured": True, "bridge_ip": config.bridge_ip}

        if new_ip != config.bridge_ip:
            logger.info("Bridge IP changed (%s -> %s), updating config.yaml", config.bridge_ip, new_ip)
            update_bridge_ip(new_ip)
        return {"reachable": True, "configured": True, "bridge_ip": new_ip}
