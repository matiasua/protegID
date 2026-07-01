"""Schemas de autenticación."""

from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user: UserRead


class RegisterResponse(BaseModel):
    user: UserRead
    verification_required: bool


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=512)


class VerifyEmailResponse(BaseModel):
    email_verified: bool


class ResendVerificationResponse(BaseModel):
    verification_required: bool
    verification_sent: bool
