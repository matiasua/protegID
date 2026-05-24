"""Persistencia de códigos QR de dispositivos en S3/MinIO."""

from botocore.exceptions import ClientError

from app.core.settings import get_settings
from app.core.storage import get_s3_client
from app.services.qr_codes import generate_public_profile_qr_png_bytes


QR_CONTENT_TYPE = "image/png"


def get_qr_object_key(public_id: str) -> str:
    return f"qr/devices/{public_id}.png"


def get_device_qr_object_key(public_id: str) -> str:
    return get_qr_object_key(public_id)


def upload_device_qr(public_id: str) -> str:
    object_key = get_device_qr_object_key(public_id)
    png_bytes = generate_public_profile_qr_png_bytes(public_id)

    get_s3_client().put_object(
        Bucket=_get_bucket_name(),
        Key=object_key,
        Body=png_bytes,
        ContentType=QR_CONTENT_TYPE,
    )

    return object_key


def download_device_qr(public_id: str) -> bytes:
    object_key = get_device_qr_object_key(public_id)

    try:
        response = get_s3_client().get_object(
            Bucket=_get_bucket_name(),
            Key=object_key,
        )
    except ClientError as error:
        if _is_not_found_error(error):
            raise FileNotFoundError(object_key) from error
        raise

    body = response["Body"]
    try:
        return body.read()
    finally:
        body.close()


def device_qr_exists(public_id: str) -> bool:
    try:
        get_s3_client().head_object(
            Bucket=_get_bucket_name(),
            Key=get_device_qr_object_key(public_id),
        )
    except ClientError as error:
        if _is_not_found_error(error):
            return False
        raise

    return True


def _get_bucket_name() -> str:
    bucket = get_settings().minio_bucket
    if not bucket:
        raise RuntimeError("MINIO_BUCKET is not configured")

    return bucket


def _is_not_found_error(error: ClientError) -> bool:
    code = error.response.get("Error", {}).get("Code")
    return code in {"404", "NoSuchKey", "NotFound"}
