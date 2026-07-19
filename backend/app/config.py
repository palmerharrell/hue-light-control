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
