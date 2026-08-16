import json

import respx
from httpx import Response

BRIDGE_URL = "http://192.168.x.x/api/test-api-key"


@respx.mock
async def test_create_group_scene(client):
    scenes_route = respx.post(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json=[{"success": {"id": "new123"}}])
    )
    respx.get(f"{BRIDGE_URL}/groups/3").mock(
        return_value=Response(200, json={"name": "Living Room", "lights": ["1", "2", "5"], "type": "Zone"})
    )

    resp = await client.post(
        "/api/scenes", json={"name": "Movie Night", "light_ids": ["1", "2"], "group_id": "3"}
    )

    assert resp.status_code == 201
    # A GroupScene's membership is derived from the group itself — the
    # bridge rejects a request that also includes an explicit `lights` list
    # alongside `group` (confirmed live: "Conflicting parameter" error).
    assert json.loads(scenes_route.calls.last.request.content) == {
        "name": "Movie Night",
        "recycle": False,
        "type": "GroupScene",
        "group": "3",
    }
    assert resp.json() == {
        "id": "new123",
        "name": "Movie Night",
        # Reflects the group's actual membership (3 lights), not the 2
        # light_ids that were submitted — those don't apply to a GroupScene.
        "light_count": 3,
        "light_ids": ["1", "2", "5"],
        "group_id": "3",
    }


@respx.mock
async def test_create_light_scene_without_group(client):
    scenes_route = respx.post(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json=[{"success": {"id": "new456"}}])
    )

    resp = await client.post("/api/scenes", json={"name": "Reading", "light_ids": ["1", "2"]})

    assert resp.status_code == 201
    assert json.loads(scenes_route.calls.last.request.content) == {
        "name": "Reading",
        "lights": ["1", "2"],
        "recycle": False,
        "type": "LightScene",
    }
    assert resp.json() == {
        "id": "new456",
        "name": "Reading",
        "light_count": 2,
        "light_ids": ["1", "2"],
        "group_id": None,
    }


@respx.mock
async def test_create_scene_empty_string_group_id_treated_as_no_group(client):
    # A direct API caller could send group_id: "" instead of null/omitted
    # (the frontend always normalizes to null, but the API shouldn't rely
    # on that) — it should behave exactly like no group_id was given,
    # rather than passing group="" through to the bridge and surfacing an
    # opaque 502.
    scenes_route = respx.post(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json=[{"success": {"id": "new789"}}])
    )

    resp = await client.post("/api/scenes", json={"name": "Reading", "light_ids": ["1"], "group_id": ""})

    assert resp.status_code == 201
    assert json.loads(scenes_route.calls.last.request.content) == {
        "name": "Reading",
        "lights": ["1"],
        "recycle": False,
        "type": "LightScene",
    }
    assert resp.json()["group_id"] is None


async def test_create_scene_empty_name_is_422(client):
    resp = await client.post("/api/scenes", json={"name": "", "light_ids": ["1"]})

    assert resp.status_code == 422


async def test_create_scene_empty_light_ids_is_422(client):
    resp = await client.post("/api/scenes", json={"name": "Reading", "light_ids": []})

    assert resp.status_code == 422


@respx.mock
async def test_create_group_scene_with_empty_light_ids(client):
    # The per-zone "New Scene" button (issue #30) never collects a light
    # selection — light_ids is irrelevant for a GroupScene anyway (its
    # membership comes from the group), so an empty list must be accepted
    # whenever group_id is set.
    scenes_route = respx.post(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json=[{"success": {"id": "new321"}}])
    )
    respx.get(f"{BRIDGE_URL}/groups/3").mock(
        return_value=Response(200, json={"name": "Living Room", "lights": ["1", "2"], "type": "Zone"})
    )

    resp = await client.post("/api/scenes", json={"name": "Movie Night", "light_ids": [], "group_id": "3"})

    assert resp.status_code == 201
    assert json.loads(scenes_route.calls.last.request.content) == {
        "name": "Movie Night",
        "recycle": False,
        "type": "GroupScene",
        "group": "3",
    }


@respx.mock
async def test_create_scene_bridge_error_returns_502(client):
    respx.post(f"{BRIDGE_URL}/scenes").mock(
        return_value=Response(200, json=[{"error": {"description": "invalid/missing parameters in body"}}])
    )

    resp = await client.post("/api/scenes", json={"name": "Reading", "light_ids": ["1"]})

    assert resp.status_code == 502
