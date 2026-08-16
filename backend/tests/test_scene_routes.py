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
