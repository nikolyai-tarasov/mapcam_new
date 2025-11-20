from __future__ import annotations

import asyncio
import io
import logging
import mimetypes
import uuid
from typing import BinaryIO

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from src.app.core.config import settings
from src.app.core.constants import StorageConfig
from src.app.core.exceptions import StorageError

logger = logging.getLogger(__name__)


MinioStorageError = StorageError


class MinioStorage:
    """Инкапсулирует работу с MinIO: загрузка видео и миниатюр."""

    def __init__(self) -> None:
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        self._bucket = settings.MINIO_BUCKET

    async def ensure_bucket(self) -> None:
        exists = await asyncio.to_thread(self._client.bucket_exists, self._bucket)
        if not exists:
            await asyncio.to_thread(self._client.make_bucket, self._bucket)

    async def upload_file(self, file: UploadFile, object_name: str | None = None) -> str:
        """Загружает файл в хранилище MinIO."""
        if file.content_type not in {"video/mp4", "application/octet-stream"}:
            logger.warning("Unsupported content type", extra={"content_type": file.content_type})
            raise StorageError("Unsupported content type. Only mp4 is allowed.")

        object_name = object_name or self._generate_object_name(file.filename)
        file.file.seek(0)
        await self._put_object(file.file, object_name, file.content_type or "video/mp4")
        return object_name

    async def upload_binary(
        self,
        data: BinaryIO,
        content_length: int,
        content_type: str | None,
        object_name: str | None = None,
    ) -> str:
        object_name = object_name or self._generate_object_name()
        await self._put_object(data, object_name, content_type or "application/octet-stream", content_length)
        return object_name

    async def upload_bytes(self, payload: bytes, content_type: str) -> str:
        buffer = io.BytesIO(payload)
        buffer.seek(0)
        return await self.upload_binary(buffer, len(payload), content_type)

    async def _put_object(
        self,
        file_obj: BinaryIO,
        object_name: str,
        content_type: str,
        content_length: int | None = None,
    ) -> None:
        """Загружает объект в хранилище MinIO."""
        try:
            length = content_length if content_length is not None else -1
            logger.debug("Uploading object to MinIO", extra={"object_name": object_name, "content_type": content_type})
            await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                object_name,
                file_obj,
                length,
                part_size=StorageConfig.UPLOAD_CHUNK_SIZE,
                content_type=content_type,
            )
            logger.debug("Object uploaded successfully", extra={"object_name": object_name})
        except S3Error as exc:
            logger.exception("Failed to upload object to MinIO", extra={"object_name": object_name})
            raise StorageError(f"Failed to upload object to MinIO: {exc}") from exc

    async def get_presigned_url(self, object_name: str, expires: int | None = None) -> str:
        """Генерирует предварительно подписанный URL для доступа к объекту."""
        if expires is None:
            expires = StorageConfig.PRESIGNED_URL_EXPIRE_SECONDS
        try:
            logger.debug("Generating presigned URL", extra={"object_name": object_name, "expires": expires})
            return await asyncio.to_thread(
                self._client.get_presigned_url,
                "GET",
                self._bucket,
                object_name,
                expires=expires,
            )
        except S3Error as exc:
            logger.exception("Failed to generate presigned URL", extra={"object_name": object_name})
            raise StorageError(f"Failed to generate presigned URL: {exc}") from exc

    async def remove_object(self, object_name: str) -> None:
        """Удаляет объект из хранилища MinIO."""
        try:
            logger.debug("Removing object", extra={"object_name": object_name})
            await asyncio.to_thread(self._client.remove_object, self._bucket, object_name)
            logger.debug("Object removed successfully", extra={"object_name": object_name})
        except S3Error as exc:
            logger.exception("Failed to remove object", extra={"object_name": object_name})
            raise StorageError(f"Failed to remove object {object_name}: {exc}") from exc

    async def download_object(self, object_name: str) -> bytes:
        """Скачивает объект из хранилища MinIO."""
        try:
            logger.debug("Downloading object", extra={"object_name": object_name})
            response = await asyncio.to_thread(self._client.get_object, self._bucket, object_name)
            data = await asyncio.to_thread(response.read)
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)
            logger.debug("Object downloaded successfully", extra={"object_name": object_name, "size": len(data)})
            return data
        except S3Error as exc:
            logger.exception("Failed to download object", extra={"object_name": object_name})
            raise StorageError(f"Failed to download object {object_name}: {exc}") from exc

    def _generate_object_name(self, filename: str | None = None) -> str:
        extension = ""
        if filename:
            guessed = mimetypes.guess_extension(mimetypes.guess_type(filename)[0] or "")
            if guessed:
                extension = guessed
        return f"{uuid.uuid4().hex}{extension}"


minio_storage = MinioStorage()