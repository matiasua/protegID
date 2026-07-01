"""Punto de entrada principal de ProtegID API."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.emergency_profiles import router as emergency_profiles_router
from app.api.public_devices import router as public_devices_router
from app.api.public_profiles import router as public_profiles_router
from app.api.qr_codes import router as qr_codes_router
from app.core.csrf import validate_csrf_token
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.readiness import get_readiness_status
from app.core.settings import get_settings

configure_logging()

settings = get_settings()
logger = logging.getLogger("protegid-api")
CSRF_EXEMPT_PATHS = {"/api/auth/login", "/api/auth/verify-email"}

app = FastAPI(
    title="ProtegID API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

register_exception_handlers(app)


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.url.path not in CSRF_EXEMPT_PATHS
        and settings.session_cookie_name in request.cookies
        and not validate_csrf_token(request)
    ):
        return JSONResponse(
            status_code=403,
            content={"detail": "CSRF validation failed"},
        )

    return await call_next(request)


app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(emergency_profiles_router)
app.include_router(public_devices_router)
app.include_router(public_profiles_router)
app.include_router(qr_codes_router)

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
