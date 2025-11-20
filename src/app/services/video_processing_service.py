from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from collections.abc import Callable
from typing import Any

import cv2
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.db_session import async_db_session
from src.app.models import Video
from src.app.services.storage_service import MinioStorage, minio_storage
from src.app.services.video_service import VideoService

logger = logging.getLogger(__name__)


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
        async with self._session_factory() as session:
            service = VideoService(session, storage=self._storage)
            video = await service.get_video(video_id)
            if not video:
                logger.warning("Video %s not found for processing", video_id)
                return

            await service.mark_processing_started(video)

            try:
                thumbnail_key, attributes = await self._extract_first_frame(video)
                await service.mark_processing_completed(video, thumbnail_key=thumbnail_key, attributes=attributes)
            except Exception as exc:
                await service.mark_processing_failed(video, reason=str(exc))
                logger.exception("Processing failed for video %s: %s", video_id, exc)

    async def _extract_first_frame(self, video: Video) -> tuple[str | None, dict[str, Any]]:
        payload = await self._storage.download_object(video.storage_key)

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            await asyncio.to_thread(tmp_video.write, payload)
            await asyncio.to_thread(tmp_video.flush)

            thumbnail_bytes, frame_info = await asyncio.to_thread(self._extract_frame_sync, tmp_video.name)
            thumbnail_key = await self._storage.upload_bytes(thumbnail_bytes, "image/jpeg")
            attributes = {
                "thumbnail": thumbnail_key,
                **frame_info,
            }
            return thumbnail_key, attributes

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

from src.app.services.video_processing_queue import video_processing_queue

video_processing_queue.set_processor(video_processing_service.process_video)