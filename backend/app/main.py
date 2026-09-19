from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.models import SearchRequest, SearchResponse
from app.pipeline import WhirlpoolPipeline
from app.services.clip import ClipEmbedder


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    client = httpx.AsyncClient(
        headers={"Accept": "application/json"},
        limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
    )
    clip = ClipEmbedder()
    await asyncio.to_thread(clip.initialize)
    app.state.settings = settings
    app.state.pipeline = WhirlpoolPipeline(settings, client, clip)
    app.state.clip = clip
    yield
    await client.aclose()


app = FastAPI(
    title="Whirlpool Campus Profiler API",
    version="1.0.0",
    lifespan=lifespan,
)

_startup_settings = Settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_startup_settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health(request: Request) -> dict:
    settings: Settings = request.app.state.settings
    clip: ClipEmbedder = request.app.state.clip
    return {
        "status": "ok" if not settings.missing_required_keys else "configuration_required",
        "missing_keys": settings.missing_required_keys,
        "clip_ready": clip.available,
        "ai_provider": settings.resolved_ai_provider,
        "ai_model": (
            settings.yandex_model
            if settings.resolved_ai_provider == "yandex"
            else settings.gemini_model
        ),
    }


@app.post("/api/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest, request: Request, response: Response
) -> SearchResponse:
    settings: Settings = request.app.state.settings
    if settings.missing_required_keys:
        raise HTTPException(
            status_code=503,
            detail={"missing_environment_variables": settings.missing_required_keys},
        )
    pipeline: WhirlpoolPipeline = request.app.state.pipeline
    try:
        async with asyncio.timeout(settings.pipeline_timeout_seconds):
            result = await pipeline.run(payload.university_name)
            response.headers["X-Data-Attribution"] = "© OpenStreetMap contributors"
            return result
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail="The profiling pipeline exceeded its 29-second deadline.",
        ) from exc
