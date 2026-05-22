"""Cliente S3 compatible con MinIO y health check de bucket."""

from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from app.core.settings import get_settings


@lru_cache
def get_s3_client() -> Any:
    settings = get_settings()

    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint or None,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id or None,
        aws_secret_access_key=settings.s3_secret_access_key or None,
        config=Config(s3={"addressing_style": "path"}),
    )


def check_bucket_access() -> bool:
    bucket = get_settings().minio_bucket
    if not bucket:
        raise RuntimeError("MINIO_BUCKET is not configured")

    get_s3_client().head_bucket(Bucket=bucket)
    return True
