from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from src.app.schemas.camera import CameraRead
from src.app.schemas.video import (
    VideoFilter,
    VideoProcessingResultFilter,
    VideoProcessingResultRead,
    VideoRead,
)


class LocationVideoFilter(VideoFilter):
    pass


class LocationVideosResponse(BaseModel):
    camera: CameraRead
    videos: list[VideoRead]
    total: int


class LocationAnalyticsFilter(VideoProcessingResultFilter):
    video_id: uuid.UUID | None = Field(default=None)


class LocationAnalyticsResponse(BaseModel):
    camera: CameraRead
    analyses: list[VideoProcessingResultRead]
    total: int




