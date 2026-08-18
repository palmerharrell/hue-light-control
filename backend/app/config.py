import os
import tempfile
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class BridgeConfig(BaseModel):
    bridge_ip: Optional[str] = None
    api_key: Optional[str] = None
    # Favorited scene ids (issue #58) — local UI preference, not bridge
    # data, so it lives alongside bridge_ip/api_key in the same local config
    # rather than requiring a separate store.
    favorite_scene_ids: list[str] = []


def load_config() -> BridgeConfig:
    if not CONFIG_PATH.exists():
        return BridgeConfig()
    with CONFIG_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return BridgeConfig(**data)


def _write_config(config: BridgeConfig) -> None:
    # Write-then-rename so a crash mid-write can't leave config.yaml
    # truncated (which would also lose api_key, requiring re-pairing).
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix=".config.yaml.")
    try:
        with os.fdopen(fd, "w") as f:
            yaml.safe_dump(config.model_dump(exclude_none=True), f)
        os.replace(tmp_path, CONFIG_PATH)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def update_bridge_ip(ip: str) -> None:
    config = load_config()
    config.bridge_ip = ip
    _write_config(config)


def update_favorite_scene_ids(scene_ids: list[str]) -> None:
    config = load_config()
    config.favorite_scene_ids = scene_ids
    _write_config(config)
