import colorsys
import math
from typing import Optional

import httpx
from pydantic import BaseModel

from app.config import BridgeConfig


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
    if mode == "xy" and "xy" in state:
        x, y = state["xy"]
        return _xy_to_rgb_hex(x, y)
    if mode == "hs" and "hue" in state and "sat" in state:
        return _hs_to_rgb_hex(state["hue"], state["sat"])
    if mode == "ct" and "ct" in state:
        return _ct_to_rgb_hex(state["ct"])
    return None


def _to_light(light_id: str, raw: dict) -> Light:
    state = raw.get("state", {})
    return Light(
        id=light_id,
        name=raw.get("name", f"Light {light_id}"),
        on=state.get("on", False),
        brightness_pct=round(state.get("bri", 0) / 254 * 100),
        color=_light_color(state),
        reachable=state.get("reachable", False),
    )


async def get_lights(config: BridgeConfig) -> list[Light]:
    if not config.bridge_ip or not config.api_key:
        raise BridgeNotConfigured()

    url = f"http://{config.bridge_ip}/api/{config.api_key}/lights"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise BridgeUnreachable(str(exc)) from exc

    if isinstance(data, list):
        error = data[0].get("error", {}) if data else {}
        raise BridgeUnreachable(error.get("description", "bridge returned an error"))

    return [_to_light(light_id, raw) for light_id, raw in data.items()]
