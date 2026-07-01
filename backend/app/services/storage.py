import logging
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath

from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredObject:
    object_path: str
    backend: str


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


def _safe_object_name(object_name: str) -> str:
    normalized = PurePosixPath(object_name.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts:
        raise ValueError("Invalid artifact object name")
    return str(normalized)


def _store_minio(object_name: str, content: bytes, content_type: str) -> StoredObject:
    client = ensure_bucket()
    client.put_object(
        settings.minio_bucket,
        object_name,
        BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return StoredObject(object_path=f"minio:{object_name}", backend="minio")


def _local_root() -> Path:
    root = Path(settings.local_artifact_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _store_local(object_name: str, content: bytes) -> StoredObject:
    root = _local_root()
    target = (root / Path(object_name)).resolve()
    if root != target and root not in target.parents:
        raise ValueError("Artifact path escapes the configured storage directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return StoredObject(object_path=f"local:{object_name}", backend="local")


def store_object(object_name: str, content: bytes, content_type: str) -> StoredObject:
    object_name = _safe_object_name(object_name)
    backend = settings.artifact_storage_backend.lower()
    if backend not in {"auto", "minio", "local"}:
        raise ValueError("ARTIFACT_STORAGE_BACKEND must be auto, minio, or local")
    if backend in {"auto", "minio"}:
        try:
            return _store_minio(object_name, content, content_type)
        except Exception:
            if backend == "minio":
                raise
            logger.warning("MinIO unavailable; storing %s in local artifact storage", object_name)
    return _store_local(object_name, content)


def upload_pdf_report(object_name: str, content: bytes) -> str:
    return store_object(object_name, content, "application/pdf").object_path


def read_object(object_name: str) -> bytes:
    if object_name.startswith("local:"):
        relative = _safe_object_name(object_name.removeprefix("local:"))
        root = _local_root()
        target = (root / Path(relative)).resolve()
        if root != target and root not in target.parents:
            raise ValueError("Artifact path escapes the configured storage directory")
        return target.read_bytes()

    object_name = object_name.removeprefix("minio:")
    client = ensure_bucket()
    response = client.get_object(settings.minio_bucket, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def presigned_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str | None:
    if object_name.startswith("local:"):
        return None
    object_name = object_name.removeprefix("minio:")
    client = ensure_bucket()
    return client.presigned_get_object(settings.minio_bucket, object_name, expires=expires)
