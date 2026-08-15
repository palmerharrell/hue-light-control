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


def load_config() -> BridgeConfig:
    if not CONFIG_PATH.exists():
        return BridgeConfig()
    with CONFIG_PATH.open() as f:
        data = yaml.safe_load(f) or {}
    return BridgeConfig(**data)


def update_bridge_ip(ip: str) -> None:
    config = load_config()
    config.bridge_ip = ip
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
