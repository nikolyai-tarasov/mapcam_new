from __future__ import annotations

import asyncio
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

import cv2  # type: ignore[import-untyped]
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.logging_config import get_logger, log_extra
from src.app.db.db_session import async_db_session
from src.app.models import Video
from src.app.services.storage_service import MinioStorage, minio_storage
from src.app.services.video_service import VideoService

logger = get_logger(__name__)


class VideoProcessingService:
    """Обрабатывает видео: извлекает первый кадр, обновляет статус и дополнительные атрибуты."""

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] | None = None,
        storage: MinioStorage | None = None,
    ) -> None:
        self._session_factory = session_factory or async_db_session.get_session
        self._storage = storage or minio_storage

    async def process_video(self, video_id: uuid.UUID) -> None:
        logger.info("Starting video processing", extra=log_extra(video_id=str(video_id)))
        
        async with self._session_factory() as session:
            service = VideoService(session, storage=self._storage)
            video = await service.get_video(video_id)
            if not video:
                logger.warning("Video not found for processing", extra=log_extra(video_id=str(video_id)))
                return

            await service.mark_processing_started(video)
            logger.debug("Video processing started", extra=log_extra(video_id=str(video_id)))

            try:
                thumbnail_key, attributes = await self._extract_first_frame(video)
                await service.mark_processing_completed(video, thumbnail_key=thumbnail_key, attributes=attributes)
                logger.info(
                    "Video processing completed successfully",
                    extra=log_extra(video_id=str(video_id), thumbnail_key=thumbnail_key)
                )
            except Exception as exc:  # noqa: BLE001
                await service.mark_processing_failed(video, reason=str(exc))
                logger.exception(
                    "Video processing failed",
                    extra=log_extra(video_id=str(video_id), error=str(exc))
                )

    async def _extract_first_frame(self, video: Video) -> tuple[str | None, dict[str, Any]]:
        """
        Извлекает первый кадр из видео.
        
        Использует streaming download для предотвращения загрузки
        всего файла в память.
        """
        import os
        
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            logger.debug("Downloading video for processing", extra={"video_id": str(video.id), "storage_key": video.storage_key})
            await self._storage.download_to_file(video.storage_key, tmp_path)
            
            logger.debug("Extracting first frame", extra={"video_id": str(video.id)})
            thumbnail_bytes, frame_info = await asyncio.to_thread(self._extract_frame_sync, tmp_path)
            
            logger.debug("Uploading thumbnail", extra={"video_id": str(video.id)})
            thumbnail_key = await self._storage.upload_bytes(thumbnail_bytes, "image/jpeg")
            
            attributes = {
                "thumbnail": thumbnail_key,
                **frame_info,
            }
            return thumbnail_key, attributes
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception as exc:
                    logger.warning("Failed to delete temp file", extra={"path": tmp_path, "error": str(exc)})

    @staticmethod
    def _extract_frame_sync(file_path: str) -> tuple[bytes, dict[str, Any]]:
        capture = cv2.VideoCapture(file_path)
        try:
            success, frame = capture.read()
            if not success or frame is None:
                raise RuntimeError("Unable to extract first frame from video")

            success, buffer = cv2.imencode(".jpg", frame)
            if not success:
                raise RuntimeError("Failed to encode frame to JPEG")

            height, width = frame.shape[:2]
            frame_info = {
                "frame_width": int(width),
                "frame_height": int(height),
            }
            return buffer.tobytes(), frame_info
        finally:
            capture.release()


video_processing_service = VideoProcessingService()

from src.app.services.video_processing_queue import video_processing_queue  # noqa: E402

video_processing_queue.set_processor(video_processing_service.process_video)




