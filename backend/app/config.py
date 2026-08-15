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
    with CONFIG_PATH.open("w") as f:
        yaml.safe_dump(config.model_dump(exclude_none=True), f)
