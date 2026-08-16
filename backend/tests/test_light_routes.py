import json

import respx
from httpx import Response

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


@respx.mock
async def test_set_light_on(client):
    state_route = respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/on": True}}])
    )

    resp = await client.put("/api/lights/1/state", json={"on": True})

    assert resp.status_code == 200
    assert json.loads(state_route.calls.last.request.content) == {"on": True}


@respx.mock
async def test_set_light_off(client):
    state_route = respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/on": False}}])
    )

    resp = await client.put("/api/lights/1/state", json={"on": False})

    assert resp.status_code == 200
    assert json.loads(state_route.calls.last.request.content) == {"on": False}


@respx.mock
async def test_set_light_brightness(client):
    state_route = respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/bri": 127}}])
    )

    resp = await client.put("/api/lights/1/state", json={"brightness_pct": 50})

    assert resp.status_code == 200
    assert json.loads(state_route.calls.last.request.content) == {"bri": 127}


@respx.mock
async def test_set_light_on_and_brightness(client):
    state_route = respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(
            200, json=[{"success": {"/lights/1/state/on": True}}, {"success": {"/lights/1/state/bri": 127}}]
        )
    )

    resp = await client.put("/api/lights/1/state", json={"on": True, "brightness_pct": 50})

    assert resp.status_code == 200
    assert json.loads(state_route.calls.last.request.content) == {"on": True, "bri": 127}


async def test_set_light_state_neither_field_is_400(client):
    resp = await client.put("/api/lights/1/state", json={})

    assert resp.status_code == 400


async def test_set_light_state_brightness_zero_is_422(client):
    resp = await client.put("/api/lights/1/state", json={"brightness_pct": 0})

    assert resp.status_code == 422


async def test_set_light_state_brightness_too_high_is_422(client):
    resp = await client.put("/api/lights/1/state", json={"brightness_pct": 101})

    assert resp.status_code == 422


@respx.mock
async def test_set_light_state_bridge_error_returns_502(client):
    respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"error": {"description": "parameter not available"}}])
    )

    resp = await client.put("/api/lights/1/state", json={"on": True})

    assert resp.status_code == 502


async def test_set_light_state_bridge_not_configured_returns_503(client, monkeypatch):
    from app.config import BridgeConfig

    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.put("/api/lights/1/state", json={"on": True})

    assert resp.status_code == 503
