import respx
from httpx import Response

from app.config import BridgeConfig

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"
V2_BASE = "https://192.168.x.x/clip/v2/resource"


@respx.mock
async def test_list_lights(client):
    respx.get(f"{BRIDGE_URL}/lights").mock(
        return_value=Response(
            200,
            json={
                "1": {
                    "name": "Lamp",
                    "state": {"on": True, "bri": 254, "reachable": True},
                }
            },
        )
    )

    resp = await client.get("/api/lights")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "1",
            "name": "Lamp",
            "on": True,
            "brightness_pct": 100,
            "color": None,
            "reachable": True,
        }
    ]


@respx.mock
async def test_list_scenes(client):
    respx.get(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(
            200,
            json={
                "s1": {"name": "Relax", "lights": ["1", "2"], "group": "3"},
                "s2": {"name": "Recycle scene", "lights": ["1"], "recycle": True},
            },
        )
    )
    # Deliberately no per-scene detail beyond brightness/on-off, which the
    # frontend derives by matching light_ids against /api/lights instead
    # (v1 has no concept of "is this scene active"). playing/speed do come
    # from a per-scene CLIP v2 lookup though — s1 here is mid-animation.
    respx.get(f"{V2_BASE}/scene").mock(
        return_value=Response(
            200,
            json={
                "errors": [],
                "data": [
                    {"id_v1": "/scenes/s1", "status": {"active": "dynamic_palette"}, "speed": 0.75},
                ],
            },
        )
    )

    resp = await client.get("/api/scenes")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "s1",
            "name": "Relax",
            "light_count": 2,
            "light_ids": ["1", "2"],
            "group_id": "3",
            "playing": True,
            "speed": 0.75,
        },
    ]


@respx.mock
async def test_list_scenes_v2_unreachable_defaults_to_not_playing(client):
    respx.get(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json={"s1": {"name": "Relax", "lights": ["1"], "group": "3"}})
    )
    respx.get(f"{V2_BASE}/scene").mock(return_value=Response(500))

    resp = await client.get("/api/scenes")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["playing"] is False
    assert body[0]["speed"] == 0.5


@respx.mock
async def test_list_zones(client):
    respx.get(f"{BRIDGE_URL}/groups").mock(
        return_value=Response(
            200,
            json={
                "3": {"name": "Living Room", "lights": ["1", "2"], "type": "Zone"},
                "4": {"name": "Entertainment", "lights": ["1"], "type": "Entertainment"},
            },
        )
    )

    resp = await client.get("/api/zones")

    assert resp.status_code == 200
    assert resp.json() == [
        {"id": "3", "name": "Living Room", "light_count": 2, "light_ids": ["1", "2"]},
    ]


@respx.mock
async def test_list_lights_bridge_error_returns_502(client):
    respx.get(f"{BRIDGE_URL}/lights").mock(
        return_value=Response(200, json=[{"error": {"description": "unauthorized user"}}])
    )

    resp = await client.get("/api/lights")

    assert resp.status_code == 502
    assert resp.json() == {"detail": "Bridge unreachable: unauthorized user"}


async def test_list_lights_bridge_not_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.get("/api/lights")

    assert resp.status_code == 503
    assert resp.json() == {"detail": "Bridge not configured"}
