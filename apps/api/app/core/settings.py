"""Configuración centralizada de ProtegID API."""

from functools import lru_cache
from os import getenv


class Settings:
    """Settings base leídos desde variables de entorno.

    No loguear ni exponer valores sensibles.
    """

    app_env: str
    service_name: str
    database_url: str
    redis_url: str
    s3_endpoint: str
    s3_region: str
    s3_access_key_id: str
    s3_secret_access_key: str
    minio_bucket: str

    def __init__(self) -> None:
        self.app_env = getenv("APP_ENV", "local")
        self.service_name = getenv("SERVICE_NAME", "protegid-api")
        self.database_url = getenv("DATABASE_URL", "")
        self.redis_url = getenv("REDIS_URL", "")
        self.s3_endpoint = getenv("S3_ENDPOINT", "")
        self.s3_region = getenv("S3_REGION", "us-east-1")
        self.s3_access_key_id = getenv("S3_ACCESS_KEY_ID", "")
        self.s3_secret_access_key = getenv("S3_SECRET_ACCESS_KEY", "")
        self.minio_bucket = getenv("MINIO_BUCKET", "")

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
