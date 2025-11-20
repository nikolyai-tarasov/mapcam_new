from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from src.app.models import VideoProcessingStatus, VideoStatus


class VideoBase(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class VideoCreate(BaseModel):
    camera_id: uuid.UUID | None = None
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None


class VideoRead(VideoBase):
    id: uuid.UUID
    camera_id: uuid.UUID | None
    uploader_id: uuid.UUID | None
    original_filename: str
    storage_key: str
    thumbnail_key: str | None
    content_type: str | None
    duration_seconds: int | None
    file_size_bytes: int | None
    status: VideoStatus
    processing_status: VideoProcessingStatus
    attributes: dict[str, Any] | None
    uploaded_at: datetime
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoFilter(BaseModel):
    title: str | None = None
    uploader_email: str | None = None
    camera_ids: list[uuid.UUID] | None = None
    statuses: list[VideoStatus] | None = None
    processing_statuses: list[VideoProcessingStatus] | None = None
    uploaded_from: datetime | None = None
    uploaded_to: datetime | None = None


class VideoProcessingResultRead(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    analysis_type: str
    summary: str | None
    result_payload: dict[str, Any] | None
    metrics: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoProcessingResultFilter(BaseModel):
    analysis_type: str | None = None
    created_from: datetime | None = None
    created_to: datetime | None = None


class VideoUploadRequest(BaseModel):
    camera_id: uuid.UUID

    @field_validator("camera_id")
    def ensure_camera_id(cls, value: uuid.UUID, info: ValidationInfo) -> uuid.UUID:
        if value is None:
            raise ValueError("camera_id is required")
        return value




