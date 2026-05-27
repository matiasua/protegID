"""Schemas Pydantic de ProtegID."""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterResponse,
    ResendVerificationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from app.schemas.device import DeviceActivate, DeviceCreate, DeviceRead
from app.schemas.emergency_profile import (
    EmergencyProfileCreate,
    EmergencyProfilePublicRead,
    EmergencyProfileRead,
    EmergencyProfileUpdate,
)
from app.schemas.qr_code import DeviceQrMetadata, DeviceQrStatus
from app.schemas.user import UserCreate, UserRead

__all__ = [
    "DeviceActivate",
    "DeviceCreate",
    "DeviceQrMetadata",
    "DeviceQrStatus",
    "DeviceRead",
    "EmergencyProfileCreate",
    "EmergencyProfilePublicRead",
    "EmergencyProfileRead",
    "EmergencyProfileUpdate",
    "LoginRequest",
    "LoginResponse",
    "RegisterResponse",
    "ResendVerificationResponse",
    "UserCreate",
    "UserRead",
    "VerifyEmailRequest",
    "VerifyEmailResponse",
]
