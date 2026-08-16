from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import load_config
from app.hue_client import (
    BridgeNotConfigured,
    BridgeUnreachable,
    Light,
    Scene,
    Zone,
    create_scene,
    get_group_light_count,
    get_lights,
    get_scenes,
    get_zones,
)

app = FastAPI(title="Hue Light Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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
    light_ids: list[str] = Field(..., min_length=1)
    group_id: Optional[str] = None


@app.post("/api/scenes", status_code=201)
async def create_scene_route(body: SceneCreateRequest) -> Scene:
    config = load_config()
    scene_id = await create_scene(config, body.name, body.light_ids, body.group_id)
    if body.group_id is not None:
        # A GroupScene's membership comes from the group, not light_ids the
        # caller sent (see create_scene) — fetch the true count rather than
        # synthesizing a possibly-wrong one from the request body.
        light_count = await get_group_light_count(config, body.group_id)
    else:
        light_count = len(body.light_ids)
    return Scene(id=scene_id, name=body.name, light_count=light_count, group_id=body.group_id)
