"""Punto de entrada principal de ProtegID API."""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.readiness import get_readiness_status
from app.core.settings import get_settings

configure_logging()

settings = get_settings()
logger = logging.getLogger("protegid-api")

app = FastAPI(
    title="ProtegID API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

register_exception_handlers(app)
app.include_router(auth_router)

logger.info(
    "api_started",
    extra={
        "environment": settings.app_env,
        "service": settings.service_name,
    },
)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/api/ready", tags=["system"])
def ready():
    readiness = get_readiness_status()
    payload = {"service": settings.service_name, **readiness}

    if not readiness["ready"]:
        return JSONResponse(status_code=503, content=payload)

    return payload
