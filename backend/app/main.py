import asyncio
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import Theme, add_custom_theme, load_config, remove_custom_theme, update_favorite_scene_ids
from app.hue_client import (
    BridgeNotConfigured,
    BridgeUnreachable,
    Light,
    Scene,
    Zone,
    activate_scene,
    create_scene,
    get_group_light_ids,
    get_lights,
    get_scenes,
    get_zones,
    play_scene,
    set_group_state,
    set_light_state,
    set_scene_speed,
    set_zone_brightness_for_on_lights,
    stop_scene,
)

app = FastAPI(title="Hue Light Control API")

app.add_middleware(
    CORSMiddleware,
    # Defaults to the Vite dev server's origin; the prod deploy overrides
    # this via docker-compose.yml since nginx proxies the frontend and API
    # same-origin there.
    allow_origins=[os.environ.get("CORS_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(BridgeNotConfigured)
async def bridge_not_configured_handler(request: Request, exc: BridgeNotConfigured) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Bridge not configured"})


@app.exception_handler(BridgeUnreachable)
async def bridge_unreachable_handler(request: Request, exc: BridgeUnreachable) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"Bridge unreachable: {exc}"})


@app.get("/api/health")
def health():
    config = load_config()
    return {"status": "ok", "bridge_configured": config.bridge_ip is not None}


@app.get("/api/lights")
async def list_lights() -> list[Light]:
    config = load_config()
    return await get_lights(config)


class LightStateUpdate(BaseModel):
    on: Optional[bool] = None
    # 0 isn't a settable target (that's what on: false is for) — matches
    # _pct_to_bri's floor of 1.
    brightness_pct: Optional[int] = Field(default=None, ge=1, le=100)
    # sRGB hex, e.g. "#ff8800" — converted to the bridge's xy color space in
    # set_light_state. Only meaningful for a light with supports_color=true;
    # the bridge itself rejects xy on a color-temp-only or dimmable bulb, so
    # that rejection is left to surface as a normal 502 rather than
    # duplicated here.
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    color_temp_pct: Optional[int] = Field(default=None, ge=0, le=100)


@app.put("/api/lights/{light_id}/state")
async def update_light_state(light_id: str, update: LightStateUpdate):
    if update.on is None and update.brightness_pct is None and update.color is None and update.color_temp_pct is None:
        raise HTTPException(status_code=400, detail="must set on, brightness_pct, color, and/or color_temp_pct")
    config = load_config()
    await set_light_state(
        config,
        light_id,
        on=update.on,
        brightness_pct=update.brightness_pct,
        color=update.color,
        color_temp_pct=update.color_temp_pct,
    )
    return {"status": "ok"}


@app.get("/api/scenes")
async def list_scenes() -> list[Scene]:
    config = load_config()
    return await get_scenes(config)


@app.get("/api/zones")
async def list_zones() -> list[Zone]:
    config = load_config()
    return await get_zones(config)


class SceneCreateRequest(BaseModel):
    # 32 chars is CLIP v1's actual cap, confirmed against a real bridge
    # (a 33-char name is rejected with error type 7, "invalid value").
    name: str = Field(..., min_length=1, max_length=32)
    light_ids: list[str] = Field(...)
    group_id: Optional[str] = None

    @field_validator("group_id")
    @classmethod
    def _empty_group_id_is_no_group(cls, value: Optional[str]) -> Optional[str]:
        # The frontend already normalizes "no zone selected" to null, but a
        # direct API caller could send "" instead — treat that the same way
        # rather than passing group="" through to create_scene, which the
        # bridge would reject with an opaque 502.
        return value or None

    @model_validator(mode="after")
    def _light_ids_required_without_group(self) -> "SceneCreateRequest":
        # A GroupScene's membership comes entirely from its group — light_ids
        # is only meaningful (and required) for a standalone LightScene, see
        # create_scene's docstring. The per-zone "New Scene" button doesn't
        # collect a light selection at all once a zone is fixed, so this must
        # accept an empty list whenever group_id is set.
        if self.group_id is None and not self.light_ids:
            raise ValueError("light_ids must not be empty when no group_id is given")
        return self


@app.post("/api/scenes", status_code=201)
async def create_scene_route(body: SceneCreateRequest) -> Scene:
    config = load_config()
    if body.group_id is not None:
        # A GroupScene's membership comes from the group, not light_ids the
        # caller sent (see create_scene) — fetch the true membership rather
        # than synthesizing a possibly-wrong one from the request body. This
        # doesn't depend on the scene-creation result, so run both calls
        # concurrently instead of paying for two round-trips in series.
        scene_id, light_ids = await asyncio.gather(
            create_scene(config, body.name, body.light_ids, body.group_id),
            get_group_light_ids(config, body.group_id),
        )
    else:
        scene_id = await create_scene(config, body.name, body.light_ids, body.group_id)
        light_ids = body.light_ids
    return Scene(
        id=scene_id, name=body.name, light_count=len(light_ids), light_ids=light_ids, group_id=body.group_id
    )


class SceneActivateRequest(BaseModel):
    group_id: str


@app.post("/api/scenes/{scene_id}/activate")
async def activate_scene_route(scene_id: str, body: SceneActivateRequest):
    config = load_config()
    await activate_scene(config, body.group_id, scene_id)
    return {"status": "ok"}


class ScenePlayRequest(BaseModel):
    # CLIP v2's speed range is 0-1; 0.5 mirrors the official app's default
    # slider position for a scene that hasn't been played before.
    speed: float = Field(default=0.5, ge=0, le=1)


class SceneSpeedRequest(BaseModel):
    speed: float = Field(..., ge=0, le=1)


@app.post("/api/scenes/{scene_id}/play")
async def play_scene_route(scene_id: str, body: ScenePlayRequest = ScenePlayRequest()):
    config = load_config()
    await play_scene(config, scene_id, body.speed)
    return {"status": "ok"}


@app.post("/api/scenes/{scene_id}/stop")
async def stop_scene_route(scene_id: str):
    config = load_config()
    await stop_scene(config, scene_id)
    return {"status": "ok"}


@app.put("/api/scenes/{scene_id}/speed")
async def set_scene_speed_route(scene_id: str, body: SceneSpeedRequest):
    config = load_config()
    await set_scene_speed(config, scene_id, body.speed)
    return {"status": "ok"}


class FavoritesUpdate(BaseModel):
    scene_ids: list[str]


@app.get("/api/favorites")
def list_favorites() -> list[str]:
    # Local UI preference, not bridge data — works even when the bridge
    # isn't configured, unlike the scene/zone/light routes.
    config = load_config()
    return config.favorite_scene_ids


@app.put("/api/favorites")
def update_favorites(body: FavoritesUpdate):
    update_favorite_scene_ids(body.scene_ids)
    return {"status": "ok"}


@app.get("/api/themes")
def list_custom_themes() -> list[Theme]:
    # Only user-imported themes (issue #21) — the built-in "Default - Dark"
    # / "Default - Light" themes are frontend code, same split as
    # favorites/scenes above (local preference vs. bridge/app data).
    config = load_config()
    return config.custom_themes


@app.post("/api/themes", status_code=201)
def import_theme(theme: Theme):
    if not theme.tokens:
        raise HTTPException(status_code=400, detail="theme must define at least one token")
    config = load_config()
    if any(t.id == theme.id for t in config.custom_themes):
        raise HTTPException(status_code=409, detail=f"theme id '{theme.id}' already imported")
    add_custom_theme(theme)
    return theme


@app.delete("/api/themes/{theme_id}")
def delete_custom_theme(theme_id: str):
    config = load_config()
    if not any(t.id == theme_id for t in config.custom_themes):
        raise HTTPException(status_code=404, detail="theme not found")
    remove_custom_theme(theme_id)
    return {"status": "ok"}


class ZoneStateUpdate(BaseModel):
    on: Optional[bool] = None
    # 0 isn't a settable target (that's what on: false is for) — matches
    # _pct_to_bri's floor of 1.
    brightness_pct: Optional[int] = Field(default=None, ge=1, le=100)


@app.put("/api/zones/{zone_id}/state")
async def update_zone_state(zone_id: str, update: ZoneStateUpdate):
    if update.on is None and update.brightness_pct is None:
        raise HTTPException(status_code=400, detail="must set on and/or brightness_pct")
    config = load_config()
    if update.on is not None:
        # Explicit on/off (the zone Off button, or the frontend's "drag up
        # from fully off" gesture) — applies to every light in the zone via
        # one group-action PUT, same as before.
        await set_group_state(config, zone_id, on=update.on, brightness_pct=update.brightness_pct)
    else:
        # A plain brightness drag on an already-partially-on zone shouldn't
        # wake up bulbs the user individually turned off.
        await set_zone_brightness_for_on_lights(config, zone_id, update.brightness_pct)
    return {"status": "ok"}
