import json

import respx
from httpx import Response

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


@respx.mock
async def test_update_zone_state(client):
    action_route = respx.put(f"{BRIDGE_URL}/groups/z1/action").mock(
        return_value=Response(200, json=[{"success": {"/groups/z1/action/bri": 127}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert json.loads(action_route.calls.last.request.content) == {"bri": 127}


async def test_update_zone_state_missing_brightness_pct_is_422(client):
    resp = await client.put("/api/zones/z1/state", json={})

    assert resp.status_code == 422


async def test_update_zone_state_out_of_range_brightness_pct_is_422(client):
    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 0})

    assert resp.status_code == 422


@respx.mock
async def test_update_zone_state_bridge_error_returns_502(client):
    respx.put(f"{BRIDGE_URL}/groups/z1/action").mock(
        return_value=Response(200, json=[{"error": {"description": "invalid/missing parameters in body"}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 502


async def test_update_zone_state_bridge_not_configured_returns_503(client, monkeypatch):
    from app.config import BridgeConfig

    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 503
