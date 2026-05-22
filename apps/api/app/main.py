from fastapi import FastAPI

app = FastAPI(
    title="ProtegID API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "protegid-api"}


@app.get("/api/ready", tags=["system"])
def ready() -> dict[str, str]:
    return {"status": "ready", "service": "protegid-api"}
