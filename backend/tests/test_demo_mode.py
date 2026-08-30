import importlib

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def demo_client(monkeypatch):
    monkeypatch.setenv("HUE_DEMO_MODE", "true")
    import app.mock_hue_client as mock_hue_client
    import app.main as main

    importlib.reload(mock_hue_client)
    importlib.reload(main)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    monkeypatch.delenv("HUE_DEMO_MODE", raising=False)
    importlib.reload(mock_hue_client)
    importlib.reload(main)


async def test_demo_health_reports_reachable_with_no_config(demo_client):
    resp = await demo_client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "reachable": True, "configured": True, "bridge_ip": "demo"}


async def test_demo_lights_have_fixture_data(demo_client):
    resp = await demo_client.get("/api/lights")

    assert resp.status_code == 200
    lights = resp.json()
    assert len(lights) == 13
    assert sum(1 for light in lights if light["supports_color"]) == 6
    assert sum(1 for light in lights if light["supports_color_temp"] and not light["supports_color"]) == 1
    assert sum(1 for light in lights if not light["supports_color"] and not light["supports_color_temp"]) == 6


async def test_demo_zones_and_scenes_have_fixture_data(demo_client):
    zones_resp = await demo_client.get("/api/zones")
    scenes_resp = await demo_client.get("/api/scenes")

    assert zones_resp.status_code == 200
    assert scenes_resp.status_code == 200
    assert len(zones_resp.json()) == 5
    assert len(scenes_resp.json()) == 5


async def test_demo_set_light_state_persists_in_memory(demo_client):
    resp = await demo_client.put("/api/lights/1/state", json={"on": False, "brightness_pct": 10})
    assert resp.status_code == 200

    lights = (await demo_client.get("/api/lights")).json()
    light = next(l for l in lights if l["id"] == "1")
    assert light["on"] is False
    assert light["brightness_pct"] == 10


async def test_demo_create_scene(demo_client):
    resp = await demo_client.post(
        "/api/scenes", json={"name": "Demo Scene", "light_ids": ["1", "2"], "group_id": None}
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Demo Scene"
    assert body["light_ids"] == ["1", "2"]
