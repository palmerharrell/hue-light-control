from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_config
from app.hue_client import BridgeNotConfigured, BridgeUnreachable, Light, get_lights

app = FastAPI(title="Hue Light Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    config = load_config()
    return {"status": "ok", "bridge_configured": config.bridge_ip is not None}


@app.get("/api/lights")
async def list_lights() -> list[Light]:
    config = load_config()
    try:
        return await get_lights(config)
    except BridgeNotConfigured:
        raise HTTPException(status_code=503, detail="Bridge not configured")
    except BridgeUnreachable as exc:
        raise HTTPException(status_code=502, detail=f"Bridge unreachable: {exc}")
