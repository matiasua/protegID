"""Generación de códigos QR en memoria."""

from io import BytesIO

import qrcode
from qrcode.constants import ERROR_CORRECT_M

from app.services.public_urls import build_public_profile_url


def generate_qr_png_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return buffer.getvalue()


def generate_public_profile_qr_png_bytes(public_id: str) -> bytes:
    public_profile_url = build_public_profile_url(public_id)
    return generate_qr_png_bytes(public_profile_url)
