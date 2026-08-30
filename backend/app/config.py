import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def _recovery_path() -> Path:
    # A plain (non-bind-mounted) recovery copy of config.yaml's
    # last-written content, used only as a fallback if config.yaml itself
    # is ever found empty or unparseable -- see _write_config for why
    # that's possible. Derived from CONFIG_PATH at call time (rather than
    # a fixed module-level constant) so tests can retarget both by
    # monkeypatching CONFIG_PATH alone.
    return CONFIG_PATH.parent / "config.yaml.recovery"


# Serializes every read-modify-write against config.yaml (originally just
# add_custom_theme's check-then-write, e.g. two concurrent theme imports
# both passing a duplicate-id check before either writes). Now guards every
# writer, not just that one: _write_config writes config.yaml in place
# (see its comment for why), which two overlapping writers could otherwise
# interleave into corrupt, unparseable YAML -- unlike the old tempfile+
# os.replace scheme, where the worst case was a benign lost update.
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
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError:
            # A crash mid-write (see _write_config) can leave config.yaml
            # with new content followed by a leftover fragment of the old
            # file's tail -- not just empty, but invalid YAML outright.
            data = None
    if not data:
        # Also covers the plain-empty case (crash before any bytes were
        # written) -- either way, fall back to the last-known-good recovery
        # copy rather than silently losing api_key, which would force
        # physically re-pairing at the bridge.
        data = _load_recovery_data()
    return BridgeConfig(**data)


def _load_recovery_data() -> dict:
    recovery_path = _recovery_path()
    if not recovery_path.exists():
        return {}
    with recovery_path.open() as f:
        return yaml.safe_load(f) or {}


def _write_config(config: BridgeConfig) -> None:
    content = yaml.safe_dump(config.model_dump(exclude_none=True))

    # Stage a durable recovery copy first. Unlike config.yaml itself (see
    # below), this path is an ordinary file in a normal directory, so a
    # tempfile+os.replace here is a real atomic swap -- load_config falls
    # back to it if the in-place write below is ever interrupted.
    fd, tmp_path = tempfile.mkstemp(dir=CONFIG_PATH.parent, prefix=".config.yaml.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp_path, _recovery_path())
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    # config.yaml is bind-mounted into the container as a single file in
    # prod (see docker-compose.yml's `./backend/config.yaml:/app/config.yaml`),
    # so its inode can't be atomically swapped via os.replace from inside
    # the container -- that raises "OSError: [Errno 16] Device or resource
    # busy" on the mount point. Write in place instead, writing the full
    # content before truncating so a crash here leaves the file at worst
    # containing stale trailing bytes (recoverable via the recovery copy
    # above), never an outright-empty file the way truncate-then-write would.
    mode = "r+" if CONFIG_PATH.exists() else "w"
    with CONFIG_PATH.open(mode) as f:
        f.write(content)
        f.truncate()


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
