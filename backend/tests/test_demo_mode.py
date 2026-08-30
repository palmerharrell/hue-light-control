import pytest
from httpx import ASGITransport, AsyncClient

from app import mock_hue_client


@pytest.fixture(autouse=True)
def _reset_mock_fixture_state(monkeypatch):
    # mock_hue_client's dicts are mutated in place by writes -- reset each
    # test to the fixture's own snapshot rather than leaking mutations
    # (or _next_scene_id increments) across tests.
    monkeypatch.setattr(mock_hue_client, "_lights", dict(mock_hue_client._lights))
    monkeypatch.setattr(mock_hue_client, "_scenes", dict(mock_hue_client._scenes))
    monkeypatch.setattr(mock_hue_client, "_next_scene_id", mock_hue_client._next_scene_id)


@pytest.fixture
async def demo_client(monkeypatch):
    # Route app.main's routes at the mock client without reimporting/
    # reloading app.main -- that would rebind the module's shared __dict__
    # out from under the real FastAPI app instance other tests already hold
    # a reference to (see app.main._client's docstring).
    monkeypatch.setattr("app.main._client", mock_hue_client)
    monkeypatch.setattr("app.main.DEMO_MODE", True)

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


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
    zones = zones_resp.json()
    assert len(zones) == 6
    assert len(scenes_resp.json()) == 5

    # Every light belongs to exactly one zone -- no light left stranded
    # outside the zone-based UI (frontend groups lights strictly by zone).
    zoned_light_ids = {light_id for zone in zones for light_id in zone["light_ids"]}
    assert zoned_light_ids == set(mock_hue_client._lights.keys())


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


async def test_demo_create_scene_with_unknown_group_returns_502(demo_client):
    resp = await demo_client.post(
        "/api/scenes", json={"name": "Demo Scene", "light_ids": [], "group_id": "99"}
    )

    assert resp.status_code == 502
