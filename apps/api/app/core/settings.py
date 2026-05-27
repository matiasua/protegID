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
    public_app_url: str
    public_profile_path: str
    public_profile_consent_version: str
    email_verification_token_ttl_seconds: int
    action_token_bytes: int
    email_delivery_mode: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    session_absolute_ttl_seconds: int
    session_token_bytes: int
    session_last_used_update_interval_seconds: int
    session_cookie_name: str
    session_cookie_secure: bool
    session_cookie_samesite: str
    session_cookie_path: str
    csrf_cookie_name: str
    csrf_header_name: str
    csrf_token_bytes: int

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
        self.public_app_url = getenv("PUBLIC_APP_URL", "http://localhost:8080")
        self.public_profile_path = getenv("PUBLIC_PROFILE_PATH", "/p")
        self.public_profile_consent_version = getenv(
            "PUBLIC_PROFILE_CONSENT_VERSION", "2026-05-v1"
        )
        self.email_verification_token_ttl_seconds = int(
            getenv("EMAIL_VERIFICATION_TOKEN_TTL_SECONDS", "86400")
        )
        self.action_token_bytes = int(getenv("ACTION_TOKEN_BYTES", "32"))
        self.email_delivery_mode = getenv("EMAIL_DELIVERY_MODE", "console")
        self.smtp_host = getenv("SMTP_HOST", "")
        self.smtp_port = int(getenv("SMTP_PORT", "587"))
        self.smtp_username = getenv("SMTP_USERNAME", "")
        self.smtp_password = getenv("SMTP_PASSWORD", "")
        self.smtp_from_email = getenv("SMTP_FROM_EMAIL", "no-reply@protegid.local")
        self.smtp_from_name = getenv("SMTP_FROM_NAME", "ProtegID")
        self.jwt_secret_key = getenv("JWT_SECRET_KEY", "")
        self.jwt_algorithm = getenv("JWT_ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(
            getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        )
        self.session_absolute_ttl_seconds = int(
            getenv("SESSION_ABSOLUTE_TTL_SECONDS", "604800")
        )
        self.session_token_bytes = int(getenv("SESSION_TOKEN_BYTES", "32"))
        self.session_last_used_update_interval_seconds = int(
            getenv("SESSION_LAST_USED_UPDATE_INTERVAL_SECONDS", "300")
        )
        self.session_cookie_name = getenv("SESSION_COOKIE_NAME", "protegid_session")
        self.session_cookie_secure = (
            getenv("SESSION_COOKIE_SECURE", "false").strip().lower() == "true"
        )
        self.session_cookie_samesite = getenv("SESSION_COOKIE_SAMESITE", "lax")
        self.session_cookie_path = getenv("SESSION_COOKIE_PATH", "/")
        self.csrf_cookie_name = getenv("CSRF_COOKIE_NAME", "protegid_csrf")
        self.csrf_header_name = getenv("CSRF_HEADER_NAME", "X-CSRF-Token")
        self.csrf_token_bytes = int(getenv("CSRF_TOKEN_BYTES", "32"))

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
