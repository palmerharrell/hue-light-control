import app.config as config_module
from app.config import BridgeConfig, load_config, update_bridge_ip


def test_update_bridge_ip_round_trips(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    update_bridge_ip("192.168.x.y")

    reloaded = load_config()
    assert reloaded.bridge_ip == "192.168.x.y"
    assert reloaded.api_key == "test-api-key"


def test_write_config_swaps_the_inode(tmp_path, monkeypatch):
    # The directory (not config.yaml itself) is what's bind-mounted into
    # the container in prod (see docker-compose.yml) -- confirms writes go
    # through a real tempfile+os.replace atomic swap rather than an
    # in-place write, which would raise EBUSY against a single-file mount
    # but is unnecessary (and was reverted, see #74) now that only the
    # parent directory crosses the mount boundary.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    original_inode = config_path.stat().st_ino

    update_bridge_ip("192.168.x.y")

    assert config_path.stat().st_ino != original_inode


def test_write_config_creates_parent_directory(tmp_path, monkeypatch):
    config_path = tmp_path / "data" / "config.yaml"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    update_bridge_ip("192.168.x.y")

    assert load_config().bridge_ip == "192.168.x.y"


def test_load_config_missing_file_returns_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    assert load_config() == BridgeConfig()


def test_load_config_empty_file_returns_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    assert load_config() == BridgeConfig()
