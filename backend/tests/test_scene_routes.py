import json

import respx
from httpx import Response

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


@respx.mock
async def test_activate_scene(client):
    action_route = respx.put(f"{BRIDGE_URL}/groups/g1/action").mock(
        return_value=Response(200, json=[{"success": {"/groups/g1/action/scene": "abc123"}}])
    )

    resp = await client.post("/api/scenes/abc123/activate", json={"group_id": "g1"})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert json.loads(action_route.calls.last.request.content) == {"scene": "abc123"}


async def test_activate_scene_missing_group_id_is_422(client):
    resp = await client.post("/api/scenes/abc123/activate", json={})

    assert resp.status_code == 422


@respx.mock
async def test_activate_scene_with_brightness_sends_two_sequential_puts(client):
    action_route = respx.put(f"{BRIDGE_URL}/groups/g1/action").mock(
        side_effect=[
            Response(200, json=[{"success": {"/groups/g1/action/scene": "abc123"}}]),
            Response(200, json=[{"success": {"/groups/g1/action/bri": 127}}]),
        ]
    )

    resp = await client.post(
        "/api/scenes/abc123/activate", json={"group_id": "g1", "brightness_pct": 50}
    )

    assert resp.status_code == 200
    # Confirmed against a real bridge (see HUE_API.md's "Activating a
    # scene" section): a single PUT combining scene+bri lets the scene's
    # own stored brightness win, silently ignoring the requested bri. Two
    # sequential PUTs — recall, then scale — are required instead.
    assert action_route.call_count == 2
    assert json.loads(action_route.calls[0].request.content) == {"scene": "abc123"}
    assert json.loads(action_route.calls[1].request.content) == {"bri": 127}


@respx.mock
async def test_activate_scene_with_brightness_second_put_error_returns_502(client):
    # The scene recall (first PUT) succeeds but the brightness scale
    # (second PUT) is rejected — the whole request should still surface as
    # an error, not a silent partial success.
    respx.put(f"{BRIDGE_URL}/groups/g1/action").mock(
        side_effect=[
            Response(200, json=[{"success": {"/groups/g1/action/scene": "abc123"}}]),
            Response(200, json=[{"error": {"description": "invalid/missing parameters in body"}}]),
        ]
    )

    resp = await client.post(
        "/api/scenes/abc123/activate", json={"group_id": "g1", "brightness_pct": 50}
    )

    assert resp.status_code == 502


@respx.mock
async def test_activate_scene_bridge_error_returns_502(client):
    respx.put(f"{BRIDGE_URL}/groups/g1/action").mock(
        return_value=Response(200, json=[{"error": {"description": "invalid/missing parameters in body"}}])
    )

    resp = await client.post("/api/scenes/abc123/activate", json={"group_id": "g1"})

    assert resp.status_code == 502


async def test_activate_scene_bridge_not_configured_returns_503(client, monkeypatch):
    from app.config import BridgeConfig

    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.post("/api/scenes/abc123/activate", json={"group_id": "g1"})

    assert resp.status_code == 503
