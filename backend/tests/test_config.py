import app.config as config_module
from app.config import BridgeConfig, load_config, update_bridge_ip


def test_write_config_preserves_inode(tmp_path, monkeypatch):
    # Docker bind-mounts config.yaml into the container as a single file, so
    # writing it must never replace the file's inode (e.g. via a
    # tempfile+os.replace swap) -- that raises EBUSY against a bind-mounted
    # target from inside the container. Pre-create the file (as the bind
    # mount does) and confirm the same inode is still there afterward.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    original_inode = config_path.stat().st_ino

    update_bridge_ip("192.168.x.y")

    assert config_path.stat().st_ino == original_inode
    assert load_config().bridge_ip == "192.168.x.y"


def test_update_bridge_ip_round_trips(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    update_bridge_ip("192.168.x.y")

    reloaded = load_config()
    assert reloaded.bridge_ip == "192.168.x.y"
    assert reloaded.api_key == "test-api-key"
