"""Construcción de URLs públicas estables."""

from app.core.settings import get_settings


def build_public_profile_url(public_id: str) -> str:
    settings = get_settings()
    app_url = settings.public_app_url.rstrip("/")
    profile_path = settings.public_profile_path.strip("/")
    normalized_path = f"/{profile_path}" if profile_path else ""
    normalized_public_id = public_id.strip("/")

    return f"{app_url}{normalized_path}/{normalized_public_id}"
