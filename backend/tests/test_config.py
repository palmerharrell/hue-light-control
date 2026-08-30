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


def test_write_config_leaves_a_recovery_copy(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    update_bridge_ip("192.168.x.y")

    recovery_path = tmp_path / "config.yaml.recovery"
    assert recovery_path.exists()
    assert "192.168.x.y" in recovery_path.read_text()


def test_load_config_falls_back_to_recovery_when_config_yaml_is_empty(tmp_path, monkeypatch):
    # Simulates the crash this fix targets: config.yaml left empty by an
    # interrupted in-place write, with the recovery copy from the last
    # successful write still intact.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    (tmp_path / "config.yaml.recovery").write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    result = load_config()

    assert result.bridge_ip == "192.168.x.x"
    assert result.api_key == "test-api-key"


def test_load_config_empty_with_no_recovery_copy_returns_defaults(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    result = load_config()

    assert result == BridgeConfig()


def test_load_config_falls_back_to_recovery_on_corrupt_yaml(tmp_path, monkeypatch):
    # Simulates a crash in the write-before-truncate window when the new
    # content is shorter than the old: config.yaml ends up as valid new
    # content followed by a leftover fragment of the old file's tail,
    # which is likely to fail to parse outright rather than just come back
    # empty -- this must fall back to the recovery copy too, not 500.
    config_path = tmp_path / "config.yaml"
    config_path.write_text("bridge_ip: 192.168.x.y\n  - broken: [unterminated\n")
    (tmp_path / "config.yaml.recovery").write_text("bridge_ip: 192.168.x.x\napi_key: test-api-key\n")
    monkeypatch.setattr(config_module, "CONFIG_PATH", config_path)

    result = load_config()

    assert result.bridge_ip == "192.168.x.x"
    assert result.api_key == "test-api-key"
