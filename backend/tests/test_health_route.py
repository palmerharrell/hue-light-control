from app.config import BridgeConfig


async def test_health_reports_reachable_when_bridge_ok(client, monkeypatch):
    async def fake_ensure_bridge_reachable(config):
        return {"reachable": True, "configured": True, "bridge_ip": "192.168.x.x"}

    monkeypatch.setattr("app.main.ensure_bridge_reachable", fake_ensure_bridge_reachable)

    resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "reachable": True,
        "configured": True,
        "bridge_ip": "192.168.x.x",
    }


async def test_health_reports_unreachable_but_returns_200_when_repair_fails(client, monkeypatch):
    async def fake_ensure_bridge_reachable(config):
        return {"reachable": False, "configured": True, "bridge_ip": "192.168.x.x"}

    monkeypatch.setattr("app.main.ensure_bridge_reachable", fake_ensure_bridge_reachable)

    resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json()["reachable"] is False


async def test_health_not_configured(client, monkeypatch):
    monkeypatch.setattr("app.main.load_config", lambda: BridgeConfig(bridge_ip=None, api_key=None))

    async def fake_ensure_bridge_reachable(config):
        return {"reachable": False, "configured": False, "bridge_ip": None}

    monkeypatch.setattr("app.main.ensure_bridge_reachable", fake_ensure_bridge_reachable)

    resp = await client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "reachable": False,
        "configured": False,
        "bridge_ip": None,
    }
