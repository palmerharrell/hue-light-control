from app.config import BridgeConfig, Theme


async def test_list_themes_empty_by_default(client):
    resp = await client.get("/api/themes")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_themes_returns_configured_themes(client, monkeypatch):
    monkeypatch.setattr(
        "app.main.load_config",
        lambda: BridgeConfig(custom_themes=[Theme(id="t1", name="Test Theme", tokens={"--bg": "#000"})]),
    )

    resp = await client.get("/api/themes")

    assert resp.status_code == 200
    assert resp.json() == [{"id": "t1", "name": "Test Theme", "tokens": {"--bg": "#000"}}]


async def test_list_themes_works_without_bridge_configured(client, monkeypatch):
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.get("/api/themes")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_import_theme_persists_and_returns_it(client, monkeypatch):
    saved = {}
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())
    monkeypatch.setattr("app.main.add_custom_theme", lambda theme: saved.setdefault("theme", theme))

    resp = await client.post(
        "/api/themes", json={"id": "default-light", "name": "Default - Light", "tokens": {"--bg": "#fff"}}
    )

    assert resp.status_code == 201
    assert resp.json() == {"id": "default-light", "name": "Default - Light", "tokens": {"--bg": "#fff"}}
    assert saved["theme"].id == "default-light"


async def test_import_theme_missing_field_is_422(client):
    resp = await client.post("/api/themes", json={"id": "t1", "name": "Test"})

    assert resp.status_code == 422


async def test_import_theme_empty_tokens_is_400(client):
    resp = await client.post("/api/themes", json={"id": "t1", "name": "Test", "tokens": {}})

    assert resp.status_code == 400


async def test_import_theme_duplicate_id_is_409(client, monkeypatch):
    # add_custom_theme does its own duplicate check internally (against a
    # lock, to close a check-then-write race — see config.py), using
    # app.config's load_config rather than main's, so that's what needs
    # patching here rather than app.main.load_config.
    monkeypatch.setattr(
        "app.config.load_config",
        lambda: BridgeConfig(custom_themes=[Theme(id="t1", name="Existing", tokens={"--bg": "#000"})]),
    )

    resp = await client.post("/api/themes", json={"id": "t1", "name": "New", "tokens": {"--bg": "#fff"}})

    assert resp.status_code == 409


async def test_delete_theme_removes_it(client, monkeypatch):
    removed = {}
    monkeypatch.setattr(
        "app.main.load_config",
        lambda: BridgeConfig(custom_themes=[Theme(id="t1", name="Existing", tokens={"--bg": "#000"})]),
    )
    monkeypatch.setattr("app.main.remove_custom_theme", lambda theme_id: removed.setdefault("id", theme_id))

    resp = await client.delete("/api/themes/t1")

    assert resp.status_code == 200
    assert removed["id"] == "t1"


async def test_delete_theme_not_found_is_404(client, monkeypatch):
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig())

    resp = await client.delete("/api/themes/missing")

    assert resp.status_code == 404
