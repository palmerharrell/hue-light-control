import respx
from httpx import Response

from app.bridge_discovery import ensure_bridge_reachable
from app.config import BridgeConfig

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


async def test_ensure_bridge_reachable_not_configured():
    # No network calls should be attempted at all -- respx isn't even
    # active here, so any HTTP call would error with a real connection.
    config = BridgeConfig(bridge_ip=None, api_key=None)

    result = await ensure_bridge_reachable(config)

    assert result == {"reachable": False, "configured": False, "bridge_ip": None}


@respx.mock
async def test_ensure_bridge_reachable_verifies_current_ip_ok(monkeypatch):
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    async def fail_if_called(api_key):
        raise AssertionError("rediscovery should not run when the current IP still verifies")

    monkeypatch.setattr("app.bridge_discovery.rediscover_bridge_ip", fail_if_called)

    respx.get(f"{BRIDGE_URL}/config").mock(return_value=Response(200, json={"name": "bridge"}))

    result = await ensure_bridge_reachable(config)

    assert result == {"reachable": True, "configured": True, "bridge_ip": "192.168.x.x"}


@respx.mock
async def test_ensure_bridge_reachable_repairs_stale_ip(monkeypatch):
    # Simulates the exact gap being fixed: the stale IP belongs to some other
    # live device that answers, but not with our bridge's shape.
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    respx.get(f"{BRIDGE_URL}/config").mock(
        return_value=Response(200, json=[{"error": {"description": "unauthorized user"}}])
    )

    async def fake_rediscover(api_key):
        return "192.168.x.y"

    updated = {}

    def fake_update_bridge_ip(ip):
        updated["ip"] = ip

    monkeypatch.setattr("app.bridge_discovery.load_config", lambda: config)
    monkeypatch.setattr("app.bridge_discovery.rediscover_bridge_ip", fake_rediscover)
    monkeypatch.setattr("app.bridge_discovery.update_bridge_ip", fake_update_bridge_ip)

    result = await ensure_bridge_reachable(config)

    assert result == {"reachable": True, "configured": True, "bridge_ip": "192.168.x.y"}
    assert updated["ip"] == "192.168.x.y"


@respx.mock
async def test_ensure_bridge_reachable_total_failure_returns_clean_status(monkeypatch):
    config = BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")

    respx.get(f"{BRIDGE_URL}/config").mock(
        return_value=Response(200, json=[{"error": {"description": "unauthorized user"}}])
    )

    async def fake_rediscover(api_key):
        return None

    monkeypatch.setattr("app.bridge_discovery.load_config", lambda: config)
    monkeypatch.setattr("app.bridge_discovery.rediscover_bridge_ip", fake_rediscover)

    result = await ensure_bridge_reachable(config)

    assert result == {"reachable": False, "configured": True, "bridge_ip": "192.168.x.x"}
