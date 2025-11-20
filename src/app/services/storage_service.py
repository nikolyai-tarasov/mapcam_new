from __future__ import annotations

import asyncio
import io
import mimetypes
import uuid
from typing import BinaryIO

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from src.app.core.config import settings
from src.app.core.constants import StorageConfig
from src.app.core.exceptions import MinioStorageError
from src.app.core.logging_config import get_logger, log_extra

logger = get_logger(__name__)


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
        """
        Загрузить файл в хранилище.
        
        Args:
            file: UploadFile из FastAPI
            object_name: Имя объекта (если не указано, генерируется автоматически)
        
        Returns:
            Имя загруженного объекта
        """
        if file.content_type not in {"video/mp4", "application/octet-stream"}:
            logger.warning("Unsupported content type", extra=log_extra(content_type=file.content_type))
            raise MinioStorageError("Unsupported content type. Only mp4 is allowed.")

        object_name = object_name or self._generate_object_name(file.filename)
        file.file.seek(0)
        logger.debug("Uploading file to storage", extra=log_extra(object_name=object_name, filename=file.filename))
        await self._put_object(file.file, object_name, file.content_type or "video/mp4")
        logger.debug("File uploaded successfully", extra=log_extra(object_name=object_name))
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
        try:
            length = content_length if content_length is not None else -1
            await asyncio.to_thread(
                self._client.put_object,
                self._bucket,
                object_name,
                file_obj,
                length,
                part_size=StorageConfig.UPLOAD_CHUNK_SIZE,
                content_type=content_type,
            )
        except S3Error as exc:
            raise MinioStorageError(f"Failed to upload object to MinIO: {exc}") from exc

    async def get_presigned_url(self, object_name: str, expires: int | None = None) -> str:
        """
        Получить presigned URL для объекта.
        
        Args:
            object_name: Имя объекта
            expires: Время жизни URL в секундах (по умолчанию из конфига)
        
        Returns:
            Presigned URL
        """
        if expires is None:
            expires = StorageConfig.PRESIGNED_URL_EXPIRE_SECONDS
        
        try:
            return await asyncio.to_thread(
                self._client.get_presigned_url,
                "GET",
                self._bucket,
                object_name,
                expires=expires,
            )
        except S3Error as exc:
            logger.error("Failed to generate presigned URL", extra=log_extra(object_name=object_name, error=str(exc)))
            raise MinioStorageError(f"Failed to generate presigned URL: {exc}") from exc

    async def remove_object(self, object_name: str) -> None:
        try:
            await asyncio.to_thread(self._client.remove_object, self._bucket, object_name)
        except S3Error as exc:
            raise MinioStorageError(f"Failed to remove object {object_name}: {exc}") from exc

    async def download_object(self, object_name: str) -> bytes:
        """
        Скачать объект в память.
        
        ВНИМАНИЕ: Для больших файлов используйте download_to_file.
        
        Args:
            object_name: Имя объекта
        
        Returns:
            Содержимое объекта как bytes
        """
        try:
            response = await asyncio.to_thread(self._client.get_object, self._bucket, object_name)
            data = await asyncio.to_thread(response.read)
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)
            return data
        except S3Error as exc:
            logger.error("Failed to download object", extra=log_extra(object_name=object_name, error=str(exc)))
            raise MinioStorageError(f"Failed to download object {object_name}: {exc}") from exc
    
    async def download_to_file(self, object_name: str, file_path: str) -> None:
        """
        Скачать объект напрямую в файл (streaming).
        
        Используется для больших файлов, чтобы избежать загрузки всего файла в память.
        
        Args:
            object_name: Имя объекта в хранилище
            file_path: Путь к файлу для сохранения
        """
        try:
            logger.debug("Downloading object to file", extra=log_extra(object_name=object_name, file_path=file_path))
            await asyncio.to_thread(
                self._client.fget_object,
                self._bucket,
                object_name,
                file_path,
            )
            logger.debug("Object downloaded to file successfully", extra=log_extra(object_name=object_name))
        except S3Error as exc:
            logger.error("Failed to download object to file", extra=log_extra(object_name=object_name, file_path=file_path, error=str(exc)))
            raise MinioStorageError(f"Failed to download object {object_name} to file: {exc}") from exc

    def _generate_object_name(self, filename: str | None = None) -> str:
        extension = ""
        if filename:
            guessed = mimetypes.guess_extension(mimetypes.guess_type(filename)[0] or "")
            if guessed:
                extension = guessed
        return f"{uuid.uuid4().hex}{extension}"


minio_storage = MinioStorage()




