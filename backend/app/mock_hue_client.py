"""In-memory stand-in for hue_client.py, used when HUE_DEMO_MODE is set (see
main.py). Lets the app run and be demoed -- e.g. for portfolio purposes --
with no real Hue Bridge on the network.

Fixture shape (light type mix, zone layout) mirrors a real bridge's
docs/hue-bridge-catalog.md (6x Dimmable, 6x Extended color, 1x Color
temperature), not any invented arrangement, so the demo represents an
actual owned setup. All names/rooms below are generic, not this app's real
room names.

Every function here matches the signature of its hue_client.py counterpart
so main.py's route bodies are unaware which one they're calling. State
lives in module-level dicts, seeded fresh on import and mutated in place by
writes -- resets to the fixture on every process restart, which is fine for
a demo.
"""

from typing import Optional

from app.hue_client import BridgeUnreachable, Light, Scene, Zone

_lights: dict[str, Light] = {
    # Living Room: Extended color
    "1": Light(id="1", name="Living Room Lamp", on=True, brightness_pct=80, color="#ffb366", supports_color=True, supports_color_temp=True, reachable=True),
    "2": Light(id="2", name="Living Room Floor", on=True, brightness_pct=65, color="#ffb366", supports_color=True, supports_color_temp=True, reachable=True),
    "3": Light(id="3", name="Living Room Accent", on=False, brightness_pct=50, color="#7fd4ff", supports_color=True, supports_color_temp=True, reachable=True),
    # Bedroom: Extended color
    "4": Light(id="4", name="Bedroom Nightstand Left", on=False, brightness_pct=30, color="#ff8080", supports_color=True, supports_color_temp=True, reachable=True),
    "5": Light(id="5", name="Bedroom Nightstand Right", on=False, brightness_pct=30, color="#ff8080", supports_color=True, supports_color_temp=True, reachable=True),
    "6": Light(id="6", name="Bedroom Ceiling", on=True, brightness_pct=45, color="#fff2cc", supports_color=True, supports_color_temp=True, reachable=True),
    # Kitchen: Dimmable
    "7": Light(id="7", name="Kitchen Under-Cabinet 1", on=True, brightness_pct=100, supports_color=False, supports_color_temp=False, reachable=True),
    "8": Light(id="8", name="Kitchen Under-Cabinet 2", on=True, brightness_pct=100, supports_color=False, supports_color_temp=False, reachable=True),
    "9": Light(id="9", name="Kitchen Island", on=True, brightness_pct=90, supports_color=False, supports_color_temp=False, reachable=True),
    # Hallway: Dimmable
    "10": Light(id="10", name="Hallway Sconce 1", on=False, brightness_pct=40, supports_color=False, supports_color_temp=False, reachable=True),
    "11": Light(id="11", name="Hallway Sconce 2", on=False, brightness_pct=40, supports_color=False, supports_color_temp=False, reachable=True),
    # Closet: Dimmable
    "12": Light(id="12", name="Closet", on=False, brightness_pct=100, supports_color=False, supports_color_temp=False, reachable=True),
    # Office: Color temperature
    "13": Light(id="13", name="Office Desk Lamp", on=True, brightness_pct=70, color_temp_pct=60, supports_color=False, supports_color_temp=True, reachable=True),
}

_zones: dict[str, Zone] = {
    "1": Zone(id="1", name="Living Room", light_count=3, light_ids=["1", "2", "3"]),
    "2": Zone(id="2", name="Bedroom", light_count=3, light_ids=["4", "5", "6"]),
    "3": Zone(id="3", name="Kitchen", light_count=3, light_ids=["7", "8", "9"]),
    "4": Zone(id="4", name="Hallway", light_count=2, light_ids=["10", "11"]),
    "5": Zone(id="5", name="Office", light_count=1, light_ids=["13"]),
    "6": Zone(id="6", name="Closet", light_count=1, light_ids=["12"]),
}

_scenes: dict[str, Scene] = {
    "1": Scene(id="1", name="Relax", light_count=3, light_ids=["1", "2", "3"], group_id="1", playing=False, speed=0.5),
    "2": Scene(id="2", name="Movie Night", light_count=3, light_ids=["1", "2", "3"], group_id="1", playing=False, speed=0.3),
    "3": Scene(id="3", name="Bright", light_count=3, light_ids=["4", "5", "6"], group_id="2", playing=False, speed=0.5),
    "4": Scene(id="4", name="Wind Down", light_count=3, light_ids=["4", "5", "6"], group_id="2", playing=True, speed=0.4),
    "5": Scene(id="5", name="Cooking", light_count=3, light_ids=["7", "8", "9"], group_id="3", playing=False, speed=0.5),
}

_next_scene_id = 6


async def get_lights(config) -> list[Light]:
    return list(_lights.values())


async def set_light_state(
    config,
    light_id: str,
    *,
    on: Optional[bool] = None,
    brightness_pct: Optional[int] = None,
    color: Optional[str] = None,
    color_temp_pct: Optional[int] = None,
) -> None:
    light = _lights.get(light_id)
    if light is None:
        return
    updates = {}
    if on is not None:
        updates["on"] = on
    if brightness_pct is not None:
        updates["brightness_pct"] = brightness_pct
    if color is not None:
        updates["color"] = color
    if color_temp_pct is not None:
        updates["color_temp_pct"] = color_temp_pct
    _lights[light_id] = light.model_copy(update=updates)


async def get_scenes(config) -> list[Scene]:
    return list(_scenes.values())


async def get_zones(config) -> list[Zone]:
    return list(_zones.values())


async def create_scene(config, name: str, light_ids: list[str], group_id: Optional[str] = None) -> str:
    global _next_scene_id
    if group_id is not None and group_id not in _zones:
        raise BridgeUnreachable(f"zone {group_id} does not exist")
    scene_id = str(_next_scene_id)
    _next_scene_id += 1
    resolved_light_ids = _zones[group_id].light_ids if group_id is not None else light_ids
    _scenes[scene_id] = Scene(
        id=scene_id,
        name=name,
        light_count=len(resolved_light_ids),
        light_ids=resolved_light_ids,
        group_id=group_id,
    )
    return scene_id


async def activate_scene(config, group_id: str, scene_id: str) -> None:
    scene = _scenes.get(scene_id)
    if scene is None:
        return
    for light_id in scene.light_ids:
        light = _lights.get(light_id)
        if light is not None:
            _lights[light_id] = light.model_copy(update={"on": True})


async def play_scene(config, scene_id: str, speed: float) -> None:
    scene = _scenes.get(scene_id)
    if scene is not None:
        _scenes[scene_id] = scene.model_copy(update={"playing": True, "speed": speed})


async def stop_scene(config, scene_id: str) -> None:
    scene = _scenes.get(scene_id)
    if scene is not None:
        _scenes[scene_id] = scene.model_copy(update={"playing": False})


async def set_scene_speed(config, scene_id: str, speed: float) -> None:
    scene = _scenes.get(scene_id)
    if scene is not None:
        _scenes[scene_id] = scene.model_copy(update={"speed": speed})


async def get_group_light_ids(config, group_id: str) -> list[str]:
    zone = _zones.get(group_id)
    return zone.light_ids if zone else []


async def set_group_state(config, group_id: str, *, on: Optional[bool] = None, brightness_pct: Optional[int] = None) -> None:
    zone = _zones.get(group_id)
    if zone is None:
        return
    for light_id in zone.light_ids:
        light = _lights.get(light_id)
        if light is None:
            continue
        updates = {}
        if on is not None:
            updates["on"] = on
        if brightness_pct is not None:
            updates["brightness_pct"] = brightness_pct
        _lights[light_id] = light.model_copy(update=updates)


async def set_zone_brightness_for_on_lights(config, group_id: str, brightness_pct: int) -> None:
    zone = _zones.get(group_id)
    if zone is None:
        return
    for light_id in zone.light_ids:
        light = _lights.get(light_id)
        if light is not None and light.on:
            _lights[light_id] = light.model_copy(update={"brightness_pct": brightness_pct})
