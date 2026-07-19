from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_config

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
