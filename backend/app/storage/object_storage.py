from __future__ import annotations

import io
from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ObjectStorageService:
    def __init__(self) -> None:
        self._client: Minio | None = None
        self._memory_store: dict[str, bytes] = {}

    @property
    def client(self) -> Minio:
        if self._client is None:
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self._client

    def _bucket(self) -> str:
        return settings.minio_quote_evidence_bucket

    def _use_memory_fallback(self) -> bool:
        return settings.object_storage_allow_memory_fallback

    def _raise_storage_unavailable(self, exc: Exception) -> None:
        raise AppError(
            "Armazenamento de evidências indisponível.",
            status_code=503,
            code="STORAGE_UNAVAILABLE",
        ) from exc

    def ensure_bucket(self) -> None:
        bucket = self._bucket()
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
        except S3Error as exc:
            logger.warning("minio_bucket_check_failed bucket=%s error=%s", bucket, exc.code)
            if self._use_memory_fallback():
                return
            self._raise_storage_unavailable(exc)
        except Exception as exc:
            if self._use_memory_fallback():
                return
            self._raise_storage_unavailable(exc)

    def put_object(self, *, key: str, data: bytes, content_type: str) -> None:
        bucket = self._bucket()
        try:
            self.ensure_bucket()
            self.client.put_object(
                bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except (S3Error, AppError) as exc:
            if self._use_memory_fallback():
                self._memory_store[key] = data
                logger.info("object_stored_in_memory key=%s", key)
                return
            if isinstance(exc, AppError):
                raise
            self._raise_storage_unavailable(exc)
        except Exception as exc:
            if self._use_memory_fallback():
                self._memory_store[key] = data
                logger.info("object_stored_in_memory key=%s", key)
                return
            self._raise_storage_unavailable(exc)

    def copy_object(self, *, source_key: str, dest_key: str, content_type: str) -> None:
        if source_key in self._memory_store:
            if not self._use_memory_fallback():
                raise AppError(
                    "Armazenamento de evidências indisponível.",
                    status_code=503,
                    code="STORAGE_UNAVAILABLE",
                )
            self._memory_store[dest_key] = self._memory_store[source_key]
            return

        bucket = self._bucket()
        try:
            self.ensure_bucket()
            from minio.commonconfig import CopySource

            self.client.copy_object(
                bucket,
                dest_key,
                CopySource(bucket, source_key),
                metadata={"Content-Type": content_type},
            )
        except S3Error as exc:
            if self._use_memory_fallback():
                stream, _, _ = self.get_object(key=source_key)
                self.put_object(key=dest_key, data=stream.read(), content_type=content_type)
                return
            raise AppError(
                "Não foi possível copiar a evidência.",
                status_code=503,
                code="STORAGE_UNAVAILABLE",
            ) from exc

    def delete_object(self, *, key: str) -> None:
        if key in self._memory_store:
            del self._memory_store[key]
            return
        bucket = self._bucket()
        try:
            self.client.remove_object(bucket, key)
        except S3Error as exc:
            logger.warning("object_delete_failed key=%s error=%s", key, exc.code)

    def get_object(self, *, key: str) -> tuple[BinaryIO, int, str | None]:
        if key in self._memory_store:
            data = self._memory_store[key]
            return io.BytesIO(data), len(data), None
        bucket = self._bucket()
        try:
            response = self.client.get_object(bucket, key)
            data = response.read()
            response.close()
            response.release_conn()
            return io.BytesIO(data), len(data), response.headers.get("Content-Type")
        except S3Error as exc:
            if key in self._memory_store:
                data = self._memory_store[key]
                return io.BytesIO(data), len(data), None
            raise AppError(
                "Evidência não encontrada.",
                status_code=404,
                code="NOT_FOUND",
            ) from exc

    def get_presigned_url(self, *, key: str) -> str:
        if key in self._memory_store:
            return f"/api/v1/internal/memory-evidence/{key}"
        bucket = self._bucket()
        try:
            return self.client.presigned_get_object(
                bucket,
                key,
                expires=timedelta(seconds=settings.signed_url_expire_seconds),
            )
        except S3Error as exc:
            raise AppError(
                "Não foi possível gerar link de download.",
                status_code=503,
                code="STORAGE_UNAVAILABLE",
            ) from exc


_storage: ObjectStorageService | None = None


def get_object_storage() -> ObjectStorageService:
    global _storage
    if _storage is None:
        _storage = ObjectStorageService()
    return _storage
