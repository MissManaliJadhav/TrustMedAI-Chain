from datetime import timedelta
from io import BytesIO

from minio import Minio

from app.core.config import settings


def minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket(client: Minio | None = None) -> Minio:
    client = client or minio_client()
    if not client.bucket_exists(settings.minio_bucket):
        client.make_bucket(settings.minio_bucket)
    return client


def upload_pdf_report(object_name: str, content: bytes) -> str:
    client = ensure_bucket()
    client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(content),
        length=len(content),
        content_type="application/pdf",
    )
    return object_name


def read_object(object_name: str) -> bytes:
    client = ensure_bucket()
    response = client.get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presigned_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str:
    client = ensure_bucket()
    return client.presigned_get_object(settings.minio_bucket, object_name, expires=expires)
