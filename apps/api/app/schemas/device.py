"""Schemas de dispositivo."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


DeviceStatus = Literal["pending_activation", "active", "disabled", "lost"]
DeviceType = Literal["qr_nfc_tag"]


class DeviceCreate(BaseModel):
    label: str | None = Field(default=None, max_length=255)
    device_type: DeviceType = "qr_nfc_tag"


class DeviceActivate(BaseModel):
    public_id: str = Field(pattern=r"^PID-[ABCDEFGHJKLMNPQRSTUVWXYZ23456789]{10}$")


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None = None
    public_id: str
    label: str | None = None
    status: DeviceStatus
    device_type: str
    activated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
