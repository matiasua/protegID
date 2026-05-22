"""Schemas de códigos QR."""

from uuid import UUID

from pydantic import BaseModel


class DeviceQrMetadata(BaseModel):
    device_id: UUID
    public_id: str
    object_key: str
    content_type: str


class DeviceQrStatus(DeviceQrMetadata):
    exists: bool
