from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.app.models import Camera, Video, VideoProcessingResult
from src.app.schemas import (
    CameraRead,
    LocationAnalyticsFilter,
    LocationAnalyticsResponse,
    LocationVideosResponse,
    VideoFilter,
    VideoProcessingResultRead,
    VideoRead,
)
from src.app.services.camera_service import CameraService
from src.app.services.video_service import VideoService


class CameraNotFound(Exception):
    pass


class LocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._camera_service = CameraService(session)
        self._video_service = VideoService(session)

    async def get_videos(
        self,
        camera_id: uuid.UUID,
        filters: VideoFilter | None = None,
    ) -> LocationVideosResponse:
        camera = await self._camera_service.get_camera(camera_id)
        if not camera:
            raise CameraNotFound("Camera not found.")

        filters = filters or VideoFilter()
        filters.camera_ids = [camera_id]

        videos = await self._video_service.list_videos(filters)
        total = await self._video_service.count_videos(filters)

        return LocationVideosResponse(
            camera=CameraRead.model_validate(camera),
            videos=[VideoRead.model_validate(video) for video in videos],
            total=total,
        )

    async def get_analytics(
        self,
        camera_id: uuid.UUID,
        filters: LocationAnalyticsFilter | None = None,
    ) -> LocationAnalyticsResponse:
        camera = await self._camera_service.get_camera(camera_id)
        if not camera:
            raise CameraNotFound("Camera not found.")

        stmt = (
            select(VideoProcessingResult)
            .join(Video, VideoProcessingResult.video_id == Video.id)
            .options(joinedload(VideoProcessingResult.video))
            .where(Video.camera_id == camera_id)
            .order_by(VideoProcessingResult.created_at.desc())
        )

        if filters:
            if filters.analysis_type:
                stmt = stmt.where(VideoProcessingResult.analysis_type == filters.analysis_type)
            if filters.created_from:
                stmt = stmt.where(VideoProcessingResult.created_at >= filters.created_from)
            if filters.created_to:
                stmt = stmt.where(VideoProcessingResult.created_at <= filters.created_to)
            if filters.video_id:
                stmt = stmt.where(VideoProcessingResult.video_id == filters.video_id)

        result = await self._session.execute(stmt)
        analyses = list(result.scalars().unique())

        count_stmt = stmt.with_only_columns(func.count(VideoProcessingResult.id)).order_by(None)
        total_result = await self._session.execute(count_stmt)
        total = int(total_result.scalar_one())

        return LocationAnalyticsResponse(
            camera=CameraRead.model_validate(camera),
            analyses=[VideoProcessingResultRead.model_validate(item) for item in analyses],
            total=total,
        )




