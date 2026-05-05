from fastapi import FastAPI

from .router import router as v1_router

app = FastAPI(
    title="Aether Gateway",
    version="1.0.0",
    description="Unified API gateway for Aether platform workflows.",
)

app.include_router(v1_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "gateway"}

