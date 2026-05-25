"""FastAPI application entrypoint.

Run with: `uvicorn app.main:app --reload`

The app is intentionally thin: configuration, CORS, the v1 router, and a
health check. Endpoint logic lives in `app/api/v1/endpoints/`, business
logic in `app/services/`.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Startup/shutdown hook. Currently a no-op; add background workers here later."""
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Personal expense tracker API. Designed to be consumed by a web frontend "
        "(Next.js) today and a mobile app tomorrow. The OpenAPI spec at "
        "`/openapi.json` is the contract."
    ),
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"], summary="Health check")
def health() -> dict[str, str]:
    """Liveness probe. Cheap, no database touch."""
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
