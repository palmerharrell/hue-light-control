import asyncio
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import load_config
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
    set_light_state,
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


@app.put("/api/lights/{light_id}/state")
async def update_light_state(light_id: str, update: LightStateUpdate):
    if update.on is None and update.brightness_pct is None:
        raise HTTPException(status_code=400, detail="must set on and/or brightness_pct")
    config = load_config()
    await set_light_state(config, light_id, on=update.on, brightness_pct=update.brightness_pct)
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
    # Wired up in the frontend as the per-scene brightness slider (scale-
    # on-activate: moving the slider re-activates the scene at that
    # brightness). See activate_scene's docstring for the confirmed
    # two-PUT behavior this relies on.
    brightness_pct: Optional[int] = Field(default=None, ge=1, le=100)


@app.post("/api/scenes/{scene_id}/activate")
async def activate_scene_route(scene_id: str, body: SceneActivateRequest):
    config = load_config()
    await activate_scene(config, body.group_id, scene_id, brightness_pct=body.brightness_pct)
    return {"status": "ok"}
