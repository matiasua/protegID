"""Schemas de autenticación."""

from pydantic import BaseModel, EmailStr, Field, SecretStr

from app.schemas.user import UserRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: SecretStr = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user: UserRead
