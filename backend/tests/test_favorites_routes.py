from app.config import BridgeConfig


async def test_list_favorites_returns_configured_ids(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.load_config",
        lambda: BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key", favorite_scene_ids=["s1", "s2"]),
    )

    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == ["s1", "s2"]


async def test_list_favorites_empty_by_default(client):
    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_favorites_works_without_bridge_configured(client, monkeypatch):
    # Favorites are a local UI preference, not bridge data — unlike
    # /api/lights etc, this shouldn't 503 just because the bridge isn't set up.
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.get("/api/favorites")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_update_favorites_persists_ids(client, monkeypatch):
    saved = {}
    monkeypatch.setattr("app.main.update_favorite_scene_ids", lambda scene_ids: saved.setdefault("ids", scene_ids))

    resp = await client.put("/api/favorites", json={"scene_ids": ["s1", "s3"]})

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert saved["ids"] == ["s1", "s3"]


async def test_update_favorites_missing_field_is_422(client):
    resp = await client.put("/api/favorites", json={})

    assert resp.status_code == 422
