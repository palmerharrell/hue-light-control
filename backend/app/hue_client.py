import asyncio
import colorsys
import logging
import math
from typing import Optional

import httpx
from pydantic import BaseModel

from app.bridge_discovery import rediscover_bridge_ip
from app.config import BridgeConfig, load_config, update_bridge_ip

logger = logging.getLogger(__name__)

# Serializes rediscovery so concurrent requests (e.g. the frontend's
# lights + scenes calls firing together) don't each run their own SSDP/cloud
# search and race to write config.yaml.
_rediscovery_lock = asyncio.Lock()


class BridgeNotConfigured(Exception):
    pass


class BridgeUnreachable(Exception):
    pass


class Light(BaseModel):
    id: str
    name: str
    on: bool
    brightness_pct: int
    color: Optional[str] = None
    reachable: bool


class Scene(BaseModel):
    id: str
    name: str
    light_count: int
    light_ids: list[str] = []
    group_id: Optional[str] = None


class Zone(BaseModel):
    id: str
    name: str
    light_count: int
    light_ids: list[str] = []


def _to_hex(r: float, g: float, b: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255), round(b * 255))


def _xy_to_rgb_hex(x: float, y: float) -> str:
    """Philips' documented xyY -> sRGB conversion, at full brightness.

    Brightness is reported separately (brightness_pct), so this always
    renders the pure hue rather than a dimmed swatch.
    """
    z = 1.0 - x - y
    X = x / y if y > 0 else 0.0
    Z = z / y if y > 0 else 0.0

    r = X * 1.656492 - 0.354851 - Z * 0.255038
    g = -X * 0.707196 + 1.655397 + Z * 0.036152
    b = X * 0.051713 - 0.121364 + Z * 1.011530

    def gamma(c: float) -> float:
        c = max(0.0, c)
        c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return max(0.0, min(1.0, c))

    r, g, b = gamma(r), gamma(g), gamma(b)
    maxc = max(r, g, b, 1e-6)
    return _to_hex(r / maxc, g / maxc, b / maxc)


def _hs_to_rgb_hex(hue: int, sat: int) -> str:
    h = (hue % 65536) / 65535
    s = sat / 254
    r, g, b = colorsys.hsv_to_rgb(h, s, 1.0)
    return _to_hex(r, g, b)


def _ct_to_rgb_hex(mired: int) -> str:
    """Mired color temperature -> approximate RGB (Tanner Helland's fit)."""
    temp = (1_000_000 / mired) / 100
    if temp <= 66:
        r = 255.0
        g = 99.47 * math.log(temp) - 161.12 if temp > 0 else 0.0
    else:
        r = 329.7 * ((temp - 60) ** -0.133)
        g = 288.12 * ((temp - 60) ** -0.0755)
    if temp >= 66:
        b = 255.0
    elif temp <= 19:
        b = 0.0
    else:
        b = 138.52 * math.log(temp - 10) - 305.04

    def clamp(v: float) -> int:
        return max(0, min(255, round(v)))

    return "#{:02x}{:02x}{:02x}".format(clamp(r), clamp(g), clamp(b))


def _light_color(state: dict) -> Optional[str]:
    mode = state.get("colormode")
    try:
        if mode == "xy" and "xy" in state:
            x, y = state["xy"]
            return _xy_to_rgb_hex(x, y)
        if mode == "hs" and "hue" in state and "sat" in state:
            return _hs_to_rgb_hex(state["hue"], state["sat"])
        if mode == "ct" and "ct" in state:
            return _ct_to_rgb_hex(state["ct"])
    except Exception:
        # A single bulb reporting a malformed color value (e.g. ct=0)
        # shouldn't take down the whole /api/lights response.
        logger.warning("Could not compute color for light state %r", state, exc_info=True)
        return None
    return None


def _bri_to_pct(bri: int) -> int:
    return round(bri / 254 * 100)


def _pct_to_bri(pct: int) -> int:
    """Map a 0-100 brightness percent to Hue's 1-254 `bri` range.

    Never returns 0: Hue's `bri` field is 1-254, with on/off tracked
    separately via the `on` field.
    """
    return max(1, min(254, round(pct / 100 * 254)))


def _to_light(light_id: str, raw: dict) -> Light:
    state = raw.get("state", {})
    return Light(
        id=light_id,
        name=raw.get("name", f"Light {light_id}"),
        on=state.get("on", False),
        brightness_pct=_bri_to_pct(state.get("bri", 0)),
        color=_light_color(state),
        reachable=state.get("reachable", False),
    )


async def _request_bridge(
    ip: str, api_key: str, path: str, *, method: str = "GET", json_body: Optional[dict] = None
) -> dict:
    url = f"http://{ip}/api/{api_key}/{path}"
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.request(method, url, json=json_body)
        resp.raise_for_status()
        data = resp.json()

    if isinstance(data, list):
        if method == "GET":
            # The bridge's GET replies for lights/scenes/groups are always
            # dicts keyed by id — a list here is always an error condition
            # (e.g. an auth failure), never a legitimate payload shape.
            error = data[0].get("error", {}) if data else {}
            raise BridgeUnreachable(error.get("description", "bridge returned an error"))

        # Writes (PUT/POST) reply with a list of {"success": ...} and/or
        # {"error": ...} objects — that's normal, not an error signal by
        # itself. Only raise if the bridge actually reported an error.
        errors = [item["error"] for item in data if "error" in item]
        if errors:
            raise BridgeUnreachable(errors[0].get("description", "bridge returned an error"))
        return data

    return data


async def _bridge_request(
    config: BridgeConfig, path: str, *, method: str = "GET", json_body: Optional[dict] = None
) -> dict:
    # On a genuine network failure, the retry path below blindly re-sends
    # the same json_body against a rediscovered/newly-current IP. That's
    # fine for idempotent methods (GET, and PUT writes like "set brightness
    # to X" or "toggle" — resending the same target state twice is
    # harmless) but would double-fire a non-idempotent POST (e.g.
    # create_scene) if the original request actually reached the bridge
    # before the connection dropped, silently creating a duplicate. So POST
    # skips rediscovery/retry entirely on a network error and just raises —
    # the caller (a form submission) can retry manually, which is normal
    # and doesn't risk a silent duplicate.
    if not config.bridge_ip or not config.api_key:
        raise BridgeNotConfigured()

    try:
        return await _request_bridge(config.bridge_ip, config.api_key, path, method=method, json_body=json_body)
    except httpx.HTTPStatusError as exc:
        # The bridge responded (e.g. a 4xx on a bad write body) — the
        # request itself was invalid, not a connectivity problem, so don't
        # burn time on SSDP/cloud rediscovery or retry the same bad body.
        # Don't forward str(exc): it embeds the full request URL, which
        # contains api_key — log it server-side instead.
        logger.warning("Bridge at %s rejected the request: %s", config.bridge_ip, exc)
        raise BridgeUnreachable("bridge rejected the request") from exc
    except httpx.HTTPError as exc:
        # A genuine network-level failure (unreachable/timed out) — the
        # bridge may have gotten a new IP. Don't forward str(exc): same
        # api_key-leak concern as above — log it server-side instead.
        logger.warning("Could not reach bridge at %s: %s", config.bridge_ip, exc)
        if method == "POST":
            raise BridgeUnreachable("could not reach the bridge") from exc

    async with _rediscovery_lock:
        # A concurrent request may have already rediscovered and persisted a
        # working IP while we were waiting for the lock — try that first.
        current_ip = load_config().bridge_ip
        if current_ip and current_ip != config.bridge_ip:
            try:
                return await _request_bridge(current_ip, config.api_key, path, method=method, json_body=json_body)
            except httpx.HTTPStatusError as exc:
                logger.warning("Bridge at %s rejected the request: %s", current_ip, exc)
                raise BridgeUnreachable("bridge rejected the request") from exc
            except httpx.HTTPError:
                pass

        new_ip = await rediscover_bridge_ip(config.api_key)
        if new_ip is None:
            raise BridgeUnreachable("could not reach the bridge")

        try:
            data = await _request_bridge(new_ip, config.api_key, path, method=method, json_body=json_body)
        except httpx.HTTPStatusError as exc:
            logger.warning("Bridge at %s rejected the request: %s", new_ip, exc)
            raise BridgeUnreachable("bridge rejected the request") from exc
        except httpx.HTTPError as exc:
            logger.warning("Rediscovered bridge at %s also unreachable: %s", new_ip, exc)
            raise BridgeUnreachable("could not reach the bridge") from exc

        if new_ip != config.bridge_ip:
            logger.info("Bridge IP changed (%s -> %s), updating config.yaml", config.bridge_ip, new_ip)
            update_bridge_ip(new_ip)
        return data


async def get_lights(config: BridgeConfig) -> list[Light]:
    data = await _bridge_request(config, "lights")
    return [_to_light(light_id, raw) for light_id, raw in data.items()]


def _to_scene(scene_id: str, raw: dict) -> Scene:
    light_ids = raw.get("lights", [])
    return Scene(
        id=scene_id,
        name=raw.get("name", f"Scene {scene_id}"),
        light_count=len(light_ids),
        light_ids=light_ids,
        # Only GroupScenes have this; ties the scene to the group (room/zone)
        # it was created for. Absent for standalone LightScenes.
        group_id=raw.get("group"),
    )


async def get_scenes(config: BridgeConfig) -> list[Scene]:
    # A scene's *stored* brightness (from GET /scenes/<id>'s lightstates)
    # reflects whatever it looked like when created/last saved — not
    # whether it's currently applied or what its lights are actually at
    # right now. There's no bridge concept of "is this scene active" at
    # all (confirmed: group.action never records which scene, if any, was
    # last recalled). So this deliberately doesn't fetch per-scene detail —
    # the frontend instead derives each scene's live on/off + brightness by
    # matching light_ids against the already-loaded /api/lights, which is
    # both actually correct (reflects reality, not a stale snapshot) and
    # cheaper (no per-scene bridge round-trip at all).
    data = await _bridge_request(config, "scenes")
    return [
        _to_scene(scene_id, raw)
        for scene_id, raw in data.items()
        # "Recycle" scenes are bridge-internal, created by apps to save/restore
        # state (e.g. before a light effect) — not scenes a user created.
        if not raw.get("recycle", False)
    ]


def _to_zone(group_id: str, raw: dict) -> Zone:
    light_ids = raw.get("lights", [])
    return Zone(
        id=group_id,
        name=raw.get("name", f"Zone {group_id}"),
        light_count=len(light_ids),
        light_ids=light_ids,
    )


async def get_zones(config: BridgeConfig) -> list[Zone]:
    data = await _bridge_request(config, "groups")
    return [
        _to_zone(group_id, raw)
        for group_id, raw in data.items()
        # The bridge's "groups" endpoint also returns Rooms, Entertainment
        # areas, and the LightGroups apps create — only Zones are user-defined
        # cross-room groupings we want surfaced here.
        if raw.get("type") == "Zone"
    ]


async def create_scene(
    config: BridgeConfig, name: str, light_ids: list[str], group_id: Optional[str] = None
) -> str:
    """Create a scene from the given lights' *current* live state.

    CLIP v1 has no way to set target on/bri/color values in the create body
    — it snapshots whatever the lights are set to right now.

    Confirmed against a real bridge (not documented in HUE_API.md's source
    material): a GroupScene's membership is derived entirely from its
    `group` — the bridge rejects a request that includes both `group` and an
    explicit `lights` list with a "Conflicting parameter" error (type 14).
    So `light_ids` is only sent for a standalone LightScene; for a
    GroupScene it's ignored here (the caller may still send it to satisfy
    the request schema, but it plays no part in what the bridge stores).
    """
    if group_id is not None:
        body = {"name": name, "recycle": False, "type": "GroupScene", "group": group_id}
    else:
        body = {"name": name, "lights": light_ids, "recycle": False, "type": "LightScene"}
    result = await _bridge_request(config, "scenes", method="POST", json_body=body)
    return result[0]["success"]["id"]


async def set_light_state(
    config: BridgeConfig, light_id: str, *, on: Optional[bool] = None, brightness_pct: Optional[int] = None
) -> None:
    body = {}
    if on is not None:
        body["on"] = on
    if brightness_pct is not None:
        body["bri"] = _pct_to_bri(brightness_pct)
    await _bridge_request(config, f"lights/{light_id}/state", method="PUT", json_body=body)


async def activate_scene(config: BridgeConfig, group_id: str, scene_id: str) -> None:
    """Activate a scene via its owning group's action endpoint.

    Hue has no dedicated "activate scene" endpoint — scenes are applied by
    PUTting {"scene": <id>} to the group's action endpoint (see
    HUE_API.md's Scenes section). This is a PUT, so unlike create_scene's
    POST it's safe to let it go through the normal rediscovery-retry path:
    resending "activate this scene" twice is harmless.
    """
    await _bridge_request(config, f"groups/{group_id}/action", method="PUT", json_body={"scene": scene_id})


async def set_group_state(
    config: BridgeConfig, group_id: str, *, on: Optional[bool] = None, brightness_pct: Optional[int] = None
) -> None:
    """Set on/off and/or brightness for every light in a group/zone at once, independent of any scene.

    Scenes in the same zone/group share the same bulbs, so there's no such
    thing as a scene-specific brightness — this is the single source of
    truth for a zone's brightness (see issue #47). Confirmed against a real
    bridge (see HUE_API.md's "Activating a scene" section): combining
    {"scene": id, "bri": N} in one PUT lets the scene recall win and ignores
    `bri`, but a standalone {"bri": N} PUT to the group's action endpoint —
    with no scene involved — scales every light in the group as expected.
    Unlike `scene`, `on` and `bri` combine fine in a single PUT.
    """
    body = {}
    if on is not None:
        body["on"] = on
    if brightness_pct is not None:
        body["bri"] = _pct_to_bri(brightness_pct)
    await _bridge_request(config, f"groups/{group_id}/action", method="PUT", json_body=body)


async def get_group_light_ids(config: BridgeConfig, group_id: str) -> list[str]:
    """Light ids for a single group.

    Used right after creating a GroupScene to report its true membership —
    see create_scene's docstring for why that isn't simply light_ids.
    """
    data = await _bridge_request(config, f"groups/{group_id}")
    return data.get("lights", [])
