import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router as v1_router

app = FastAPI(
    title="Aether Gateway",
    version="1.0.0",
    description="Unified API gateway for Aether platform workflows.",
)

allowed_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)


@app.get("/")
def root() -> dict:
    return {
        "status": "ok",
        "service": "gateway",
        "health": "/health",
        "contracts": "/v1/contracts",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}

