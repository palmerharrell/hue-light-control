import json

import respx
from httpx import Response

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


def _mock_zone_lights(*, group_lights, light_states):
    """Mock GET /groups/z1 (membership) and GET /lights (on/off + bri) together —
    set_zone_brightness_for_on_lights fetches both before targeting on lights."""
    respx.get(f"{BRIDGE_URL}/groups/z1").mock(return_value=Response(200, json={"lights": group_lights}))
    respx.get(f"{BRIDGE_URL}/lights").mock(
        return_value=Response(
            200,
            json={
                light_id: {"name": f"Light {light_id}", "state": {**state, "reachable": True}}
                for light_id, state in light_states.items()
            },
        )
    )


@respx.mock
async def test_update_zone_state_brightness_only_targets_on_lights(client):
    _mock_zone_lights(
        group_lights=["1", "2", "3"],
        light_states={
            "1": {"on": True, "bri": 100},
            "2": {"on": False, "bri": 50},
            "3": {"on": True, "bri": 200},
        },
    )
    light1_route = respx.put(f"{BRIDGE_URL}/lights/1/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/1/state/bri": 127}}])
    )
    light2_route = respx.put(f"{BRIDGE_URL}/lights/2/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/2/state/bri": 127}}])
    )
    light3_route = respx.put(f"{BRIDGE_URL}/lights/3/state").mock(
        return_value=Response(200, json=[{"success": {"/lights/3/state/bri": 127}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert json.loads(light1_route.calls.last.request.content) == {"bri": 127}
    assert json.loads(light3_route.calls.last.request.content) == {"bri": 127}
    assert light2_route.call_count == 0


async def test_update_zone_state_neither_field_is_400(client):
    resp = await client.put("/api/zones/z1/state", json={})

    assert resp.status_code == 400


@respx.mock
async def test_update_zone_state_off(client):
    action_route = respx.put(f"{BRIDGE_URL}/groups/z1/action").mock(
        return_value=Response(200, json=[{"success": {"/groups/z1/action/on": False}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"on": False})

    assert resp.status_code == 200
    assert json.loads(action_route.calls.last.request.content) == {"on": False}


@respx.mock
async def test_update_zone_state_on_and_brightness_pct_combine(client):
    # An explicit `on` (the Off button, or the frontend's "drag up from a
    # fully-off zone" gesture) still goes through the group action, applying
    # to every light regardless of its current on/off state.
    action_route = respx.put(f"{BRIDGE_URL}/groups/z1/action").mock(
        return_value=Response(200, json=[{"success": {"/groups/z1/action/bri": 127}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"on": True, "brightness_pct": 50})

    assert resp.status_code == 200
    assert json.loads(action_route.calls.last.request.content) == {"on": True, "bri": 127}


async def test_update_zone_state_out_of_range_brightness_pct_is_422(client):
    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 0})

    assert resp.status_code == 422


@respx.mock
async def test_update_zone_state_off_bridge_error_returns_502(client):
    respx.put(f"{BRIDGE_URL}/groups/z1/action").mock(
        return_value=Response(200, json=[{"error": {"description": "invalid/missing parameters in body"}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"on": False})

    assert resp.status_code == 502


@respx.mock
async def test_update_zone_state_brightness_only_bridge_error_returns_502(client):
    respx.get(f"{BRIDGE_URL}/groups/z1").mock(
        return_value=Response(200, json=[{"error": {"description": "not found"}}])
    )

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 502


async def test_update_zone_state_bridge_not_configured_returns_503(client, monkeypatch):
    from app.config import BridgeConfig

    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.put("/api/zones/z1/state", json={"brightness_pct": 50})

    assert resp.status_code == 503
