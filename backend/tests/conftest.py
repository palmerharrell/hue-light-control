import pytest
from httpx import ASGITransport, AsyncClient

from app.config import BridgeConfig
from app.main import app


@pytest.fixture
def fake_config():
    # Placeholder-shaped values only — mirrors config.example.yaml's style.
    # Never a real bridge IP or API key.
    return BridgeConfig(bridge_ip="192.168.x.x", api_key="test-api-key")


@pytest.fixture
async def client(monkeypatch, fake_config):
    # Keep tests off the real, gitignored backend/config.yaml.
    monkeypatch.setattr("app.main.load_config", lambda: fake_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
