from app.config import BridgeConfig


async def test_list_favorites_returns_configured_ids(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.load_config",
        lambda: BridgeConfig(
            bridge_ip="192.168.x.x",
            api_key="test-api-key",
            favorite_scene_ids=["s1", "s2"],
            favorite_light_ids=["l1"],
        ),
    )

    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == {"scene_ids": ["s1", "s2"], "light_ids": ["l1"]}


async def test_list_favorites_empty_by_default(client):
    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == {"scene_ids": [], "light_ids": []}


async def test_list_favorites_works_without_bridge_configured(client, monkeypatch):
    # Favorites are a local UI preference, not bridge data — unlike
    # /api/lights etc, this shouldn't 503 just because the bridge isn't set up.
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == {"scene_ids": [], "light_ids": []}


async def test_update_favorites_persists_both_lists(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        "app.main.update_favorites",
        lambda scene_ids=None, light_ids=None: saved.update(scene_ids=scene_ids, light_ids=light_ids),
    )

    resp = await client.put("/api/favorites", json={"scene_ids": ["s1", "s3"], "light_ids": ["l2"]})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert saved == {"scene_ids": ["s1", "s3"], "light_ids": ["l2"]}


async def test_update_favorites_omitted_field_is_left_unchanged(client, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        "app.main.update_favorites",
        lambda scene_ids=None, light_ids=None: saved.update(scene_ids=scene_ids, light_ids=light_ids),
    )

    resp = await client.put("/api/favorites", json={"light_ids": ["l2"]})

    assert resp.status_code == 200
    assert saved == {"scene_ids": None, "light_ids": ["l2"]}


async def test_update_favorites_empty_body_is_422(client):
    resp = await client.put("/api/favorites", json={})

    assert resp.status_code == 422
