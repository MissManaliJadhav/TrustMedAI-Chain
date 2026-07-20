import logging
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import urllib3
from urllib3.exceptions import ConnectTimeoutError, NewConnectionError, MaxRetryError

from minio import Minio
from minio.error import MinioException

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StoredObject:
    object_path: str
    backend: str


def minio_client() -> Minio:
    """Create MinIO client with timeout configuration."""
    try:
        endpoint_parsed = urlparse(f"http://{settings.minio_endpoint}")
        endpoint = endpoint_parsed.netloc or settings.minio_endpoint
    except Exception:
        endpoint = settings.minio_endpoint
    
    timeout = urllib3.Timeout(
        connect=settings.minio_timeout_seconds,
        read=settings.minio_timeout_seconds,
    )
    http_client = urllib3.PoolManager(
        timeout=timeout,
        retries=urllib3.Retry(
            total=settings.minio_retry_total,
            connect=settings.minio_retry_total,
            read=settings.minio_retry_total,
            redirect=0,
            status=0,
        ),
    )

    return Minio(
        endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        http_client=http_client,
    )


def ensure_bucket(client: Minio | None = None) -> Minio:
    """Ensure MinIO bucket exists. Raises exception if connection fails."""
    client = client or minio_client()
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
    except (ConnectTimeoutError, NewConnectionError, MaxRetryError, MinioException) as e:
        logger.warning(
            "Failed to connect to MinIO at %s after timeout: %s. Falling back to local storage.",
            settings.minio_endpoint,
            str(e),
        )
        raise
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
        except (ConnectTimeoutError, NewConnectionError, MaxRetryError, MinioException) as e:
            if backend == "minio":
                raise
            logger.debug(
                "MinIO at %s unavailable (%s); falling back to local storage for %s",
                settings.minio_endpoint,
                type(e).__name__,
                object_name,
            )
        except Exception as e:
            if backend == "minio":
                raise
            logger.warning(
                "Error accessing MinIO at %s: %s; falling back to local storage",
                settings.minio_endpoint,
                str(e),
            )
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

    # Try to read from MinIO
    object_name = object_name.removeprefix("minio:")
    try:
        client = ensure_bucket()
        response = client.get_object(settings.minio_bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except (ConnectTimeoutError, NewConnectionError, MaxRetryError, MinioException) as e:
        logger.warning(
            "Failed to read %s from MinIO at %s (%s). Object may be stored locally or unavailable.",
            object_name,
            settings.minio_endpoint,
            type(e).__name__,
        )
        raise
    except Exception as e:
        logger.error("Error reading %s from MinIO: %s", object_name, str(e))
        raise


def presigned_download_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> str | None:
    if object_name.startswith("local:"):
        return None
    object_name = object_name.removeprefix("minio:")
    try:
        client = ensure_bucket()
        return client.presigned_get_object(settings.minio_bucket, object_name, expires=expires)
    except (ConnectTimeoutError, NewConnectionError, MaxRetryError, MinioException) as e:
        logger.warning(
            "Failed to generate presigned URL for %s from MinIO at %s (%s)",
            object_name,
            settings.minio_endpoint,
            type(e).__name__,
        )
        return None
    except Exception as e:
        logger.error("Error generating presigned URL for %s: %s", object_name, str(e))
        return None
