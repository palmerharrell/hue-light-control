import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

# Lives in its own directory (rather than directly under backend/) so that
# directory, not the single file, is what gets bind-mounted into the
# container in prod (see docker-compose.yml) -- letting _write_config's
# tempfile+os.replace do a real atomic swap from inside the container.
# Mounting the single file instead makes os.replace's inode swap raise
# "OSError: [Errno 16] Device or resource busy" against the mount point
# (see issue #74) -- this was tried and reverted (#73).
CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "config.yaml"

# Serializes every read-modify-write against config.yaml (originally just
# add_custom_theme's check-then-write, e.g. two concurrent theme imports
# both passing a duplicate-id check before either writes, then both writing
# -- the second write silently clobbering the first's).
_config_write_lock = threading.Lock()


class DuplicateThemeError(Exception):
    pass


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
    # Safe to do here (unlike writing CONFIG_PATH directly when it was
    # itself the bind-mount target, see CONFIG_PATH's comment) because the
    # bind mount is now CONFIG_PATH's parent directory, not CONFIG_PATH
    # itself -- os.replace only needs to swap an inode within that
    # directory, not across the mount boundary.
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    with _config_write_lock:
        config = load_config()
        config.bridge_ip = ip
        _write_config(config)


def update_favorite_scene_ids(scene_ids: list[str]) -> None:
    with _config_write_lock:
        config = load_config()
        config.favorite_scene_ids = scene_ids
        _write_config(config)


def add_custom_theme(theme: Theme) -> None:
    with _config_write_lock:
        config = load_config()
        if any(t.id == theme.id for t in config.custom_themes):
            raise DuplicateThemeError(theme.id)
        config.custom_themes = [*config.custom_themes, theme]
        _write_config(config)


def remove_custom_theme(theme_id: str) -> None:
    with _config_write_lock:
        config = load_config()
        config.custom_themes = [t for t in config.custom_themes if t.id != theme_id]
        _write_config(config)
