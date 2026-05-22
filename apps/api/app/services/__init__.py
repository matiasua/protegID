"""Servicios de negocio."""

from app.services.auth import UserAlreadyExistsError, authenticate_user, register_user
from app.services.public_urls import build_public_profile_url
from app.services.qr_codes import (
    generate_public_profile_qr_png_bytes,
    generate_qr_png_bytes,
)
from app.services.qr_storage import (
    device_qr_exists,
    get_device_qr_object_key,
    get_qr_object_key,
    upload_device_qr,
)

__all__ = [
    "UserAlreadyExistsError",
    "authenticate_user",
    "build_public_profile_url",
    "device_qr_exists",
    "generate_public_profile_qr_png_bytes",
    "generate_qr_png_bytes",
    "get_device_qr_object_key",
    "get_qr_object_key",
    "register_user",
    "upload_device_qr",
]
