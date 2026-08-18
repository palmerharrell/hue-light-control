import os
import tempfile
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class Theme(BaseModel):
    id: str
    name: str
    # Flat map of CSS custom-property name (e.g. "--bg") to value. Stored
    # opaquely — the backend doesn't know or care which properties the
    # frontend's stylesheet actually reads, so a theme can introduce new
    # tokens (e.g. for a future LCARS/Wipeout theme, issues #43/#42) without
    # backend changes.
    tokens: dict[str, str]


class BridgeConfig(BaseModel):
    bridge_ip: Optional[str] = None
    api_key: Optional[str] = None
    # Favorited scene ids (issue #58) — local UI preference, not bridge
    # data, so it lives alongside bridge_ip/api_key in the same local config
    # rather than requiring a separate store.
    favorite_scene_ids: list[str] = []
    # User-imported themes (issue #21). The built-in "Default - Dark" /
    # "Default - Light" themes ship as frontend code, not here — this only
    # holds themes imported at runtime via POST /api/themes.
    custom_themes: list[Theme] = []


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


def add_custom_theme(theme: Theme) -> None:
    config = load_config()
    config.custom_themes = [t for t in config.custom_themes if t.id != theme.id] + [theme]
    _write_config(config)


def remove_custom_theme(theme_id: str) -> None:
    config = load_config()
    config.custom_themes = [t for t in config.custom_themes if t.id != theme_id]
    _write_config(config)
