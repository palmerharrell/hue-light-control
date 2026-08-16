from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import load_config
from app.hue_client import (
    BridgeNotConfigured,
    BridgeUnreachable,
    Light,
    Scene,
    Zone,
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
