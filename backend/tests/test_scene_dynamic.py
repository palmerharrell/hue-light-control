import json

import respx
from httpx import Response

V2_BASE = "https://192.168.x.x/clip/v2/resource"

SCENE_LIST_RESPONSE = {
    "errors": [],
    "data": [
        {"id": "uuid-1", "id_v1": "/scenes/abc123"},
        {"id": "uuid-2", "id_v1": "/scenes/other"},
    ],
}


@respx.mock
async def test_play_scene(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))
    put_route = respx.put(f"{V2_BASE}/scene/uuid-1").mock(return_value=Response(200, json={"errors": [], "data": []}))

    resp = await client.post("/api/scenes/abc123/play", json={"speed": 0.75})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    # Two separate PUTs — the bridge rejects `recall` and `speed` combined
    # in one request (see play_scene's docstring).
    bodies = [json.loads(call.request.content) for call in put_route.calls]
    assert bodies == [{"speed": 0.75}, {"recall": {"action": "dynamic_palette"}}]


@respx.mock
async def test_play_scene_default_speed(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))
    put_route = respx.put(f"{V2_BASE}/scene/uuid-1").mock(return_value=Response(200, json={"errors": [], "data": []}))

    resp = await client.post("/api/scenes/abc123/play", json={})

    assert resp.status_code == 200
    assert json.loads(put_route.calls[0].request.content) == {"speed": 0.5}


@respx.mock
async def test_stop_scene(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))
    put_route = respx.put(f"{V2_BASE}/scene/uuid-1").mock(return_value=Response(200, json={"errors": [], "data": []}))

    resp = await client.post("/api/scenes/abc123/stop")

    assert resp.status_code == 200
    assert json.loads(put_route.calls.last.request.content) == {"recall": {"action": "static"}}


@respx.mock
async def test_set_scene_speed(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))
    put_route = respx.put(f"{V2_BASE}/scene/uuid-1").mock(return_value=Response(200, json={"errors": [], "data": []}))

    resp = await client.put("/api/scenes/abc123/speed", json={"speed": 0.2})

    assert resp.status_code == 200
    assert json.loads(put_route.calls.last.request.content) == {"speed": 0.2}


async def test_set_scene_speed_out_of_range_is_422(client):
    resp = await client.put("/api/scenes/abc123/speed", json={"speed": 1.5})

    assert resp.status_code == 422


@respx.mock
async def test_play_scene_unknown_id_returns_502(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))

    resp = await client.post("/api/scenes/nonexistent/play", json={})

    assert resp.status_code == 502


async def test_play_scene_bridge_not_configured_returns_503(client, monkeypatch):
    from app.config import BridgeConfig

    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.post("/api/scenes/abc123/play", json={})

    assert resp.status_code == 503


@respx.mock
async def test_play_scene_bridge_rejects_returns_502(client):
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(200, json=SCENE_LIST_RESPONSE))
    respx.put(f"{V2_BASE}/scene/uuid-1").mock(
        return_value=Response(400, json={"errors": [{"description": "not supported"}], "data": []})
    )

    resp = await client.post("/api/scenes/abc123/play", json={})

    assert resp.status_code == 502
