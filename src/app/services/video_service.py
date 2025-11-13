from __future__ import annotations

import mimetypes
import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.app.models import Camera, User, Video, VideoProcessingStatus, VideoStatus
from src.app.schemas import VideoCreate, VideoFilter
from src.app.services.camera_service import CameraService
from src.app.services.storage_service import MinioStorage, minio_storage
from src.app.services.video_processing_queue import video_processing_queue


class UnsupportedVideoTypeError(Exception):
    pass


class CameraNotFoundError(Exception):
    pass


class VideoService:
    def __init__(self, session: AsyncSession, storage: MinioStorage | None = None) -> None:
        self._session = session
        self._storage = storage or minio_storage
        self._camera_service = CameraService(session)

    async def upload_video(
        self,
        uploader: User | None,
        file: UploadFile,
        payload: VideoCreate,
    ) -> Video:
        await self._storage.ensure_bucket()
        self._validate_file(file)

        camera: Camera | None = None
        if payload.camera_id:
            camera = await self._camera_service.get_camera(payload.camera_id)
            if not camera:
                raise CameraNotFoundError("Camera not found.")

        object_name = await self._storage.upload_file(file)

        video = Video(
            camera=camera,
            uploader=uploader,
            title=payload.title,
            description=payload.description,
            original_filename=file.filename or object_name,
            storage_key=object_name,
            content_type=file.content_type,
            status=VideoStatus.UPLOADED,
            processing_status=VideoProcessingStatus.PENDING,
        )
        self._session.add(video)
        await self._session.commit()
        await self._session.refresh(video)

        await video_processing_queue.enqueue(video.id, uploader.id if uploader else None)
        await self._camera_service.invalidate_geojson_cache()

        return video

    async def list_videos(
        self,
        filters: VideoFilter | None = None,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Video]:
        stmt = self._build_video_query(filters)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique())

    async def count_videos(self, filters: VideoFilter | None = None) -> int:
        stmt = self._build_video_query(filters)
        count_stmt = stmt.with_only_columns(func.count(Video.id)).order_by(None)
        result = await self._session.execute(count_stmt)
        return int(result.scalar_one())

    async def get_video(self, video_id: uuid.UUID) -> Video | None:
        stmt = (
            select(Video)
            .options(joinedload(Video.camera), joinedload(Video.uploader), joinedload(Video.processing_results))
            .where(Video.id == video_id)
        )
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def delete_video(self, video: Video) -> None:
        await self._storage.remove_object(video.storage_key)
        if video.thumbnail_key:
            await self._storage.remove_object(video.thumbnail_key)
        await self._session.delete(video)
        await self._session.commit()
        await self._camera_service.invalidate_geojson_cache()

    async def mark_processing_started(self, video: Video) -> None:
        video.status = VideoStatus.PROCESSING
        video.processing_status = VideoProcessingStatus.IN_PROGRESS
        await self._session.commit()

    async def mark_processing_completed(
        self,
        video: Video,
        thumbnail_key: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        video.status = VideoStatus.READY
        video.processing_status = VideoProcessingStatus.COMPLETED
        if thumbnail_key:
            video.thumbnail_key = thumbnail_key
        if attributes:
            video.attributes = attributes
        await self._session.commit()

    async def mark_processing_failed(self, video: Video, reason: str | None = None) -> None:
        video.status = VideoStatus.FAILED
        video.processing_status = VideoProcessingStatus.FAILED
        if reason:
            video.attributes = video.attributes or {}
            video.attributes["error"] = reason
        await self._session.commit()

    def _build_video_query(self, filters: VideoFilter | None) -> Select[tuple[Video]]:
        stmt = (
            select(Video)
            .options(joinedload(Video.camera), joinedload(Video.uploader))
            .order_by(Video.uploaded_at.desc())
        )

        if not filters:
            return stmt

        conditions = []
        if filters.title:
            pattern = f"%{filters.title.lower()}%"
            conditions.append(func.lower(Video.title).like(pattern) | func.lower(Video.original_filename).like(pattern))
        if filters.uploader_email:
            stmt = stmt.join(Video.uploader)
            conditions.append(func.lower(User.email) == filters.uploader_email.lower())
        if filters.camera_ids:
            conditions.append(Video.camera_id.in_(filters.camera_ids))
        if filters.statuses:
            conditions.append(Video.status.in_(filters.statuses))
        if filters.processing_statuses:
            conditions.append(Video.processing_status.in_(filters.processing_statuses))
        if filters.uploaded_from:
            conditions.append(Video.uploaded_at >= filters.uploaded_from)
        if filters.uploaded_to:
            conditions.append(Video.uploaded_at <= filters.uploaded_to)

        if conditions:
            stmt = stmt.where(and_(*conditions))
        return stmt

    @staticmethod
    def _validate_file(file: UploadFile) -> None:
        filename = file.filename or ""
        content_type = file.content_type or mimetypes.guess_type(filename)[0] or ""
        if not filename.lower().endswith(".mp4") and content_type != "video/mp4":
            raise UnsupportedVideoTypeError("Only MP4 videos are supported.")




