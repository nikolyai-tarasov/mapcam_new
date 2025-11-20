from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from src.app.api.dependencies import get_current_user, get_video_service
from src.app.api.helpers import ensure_found
from src.app.core.exceptions import AuthorizationError, VideoNotFoundError
from src.app.models import User
from src.app.schemas import VideoCreate, VideoFilter, VideoProcessingResultRead, VideoRead
from src.app.services.video_service import VideoService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("/", response_model=list[VideoRead])
async def list_videos(
    title: str | None = Query(default=None),
    uploader_email: str | None = Query(default=None),
    camera_ids: Annotated[list[uuid.UUID] | None, Query()] = None,
    statuses: Annotated[list[str] | None, Query()] = None,
    processing_statuses: Annotated[list[str] | None, Query()] = None,
    uploaded_from: datetime | None = Query(default=None),
    uploaded_to: datetime | None = Query(default=None),
    limit: int | None = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    video_service: VideoService = Depends(get_video_service),
) -> list[VideoRead]:
    filters = VideoFilter(
        title=title,
        uploader_email=uploader_email,
        camera_ids=camera_ids,
        statuses=statuses,
        processing_statuses=processing_statuses,
        uploaded_from=uploaded_from,
        uploaded_to=uploaded_to,
    )
    videos = await video_service.list_videos(filters, limit=limit, offset=offset)
    return [VideoRead.model_validate(video) for video in videos]


@router.get("/{video_id}", response_model=VideoRead)
async def get_video(
    video_id: uuid.UUID,
    video_service: VideoService = Depends(get_video_service),
) -> VideoRead:
    """Получает видео по ID."""
    logger.debug("Getting video", extra={"video_id": str(video_id)})
    video = ensure_found(await video_service.get_video(video_id), "Video")
    return VideoRead.model_validate(video)


@router.post("/upload", response_model=VideoRead, status_code=status.HTTP_201_CREATED)
async def upload_video(
    camera_id: uuid.UUID = Form(...),
    title: str | None = Form(default=None),
    description: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> VideoRead:
    """Загружает видеофайл."""
    logger.info(
        "Video upload request",
        extra={
            "user_id": str(current_user.id),
            "camera_id": str(camera_id),
            "filename": file.filename,
        }
    )
    payload = VideoCreate(camera_id=camera_id, title=title, description=description)
    video = await video_service.upload_video(current_user, file, payload)
    return VideoRead.model_validate(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video(
    video_id: uuid.UUID,
    video_service: VideoService = Depends(get_video_service),
    current_user: User = Depends(get_current_user),
) -> None:
    """Удаляет видео."""
    logger.info("Video delete request", extra={"video_id": str(video_id), "user_id": str(current_user.id)})
    video = ensure_found(await video_service.get_video(video_id), "Video")
    if video.uploader_id and video.uploader_id != current_user.id:
        logger.warning(
            "Unauthorized video deletion attempt",
            extra={"video_id": str(video_id), "user_id": str(current_user.id), "owner_id": str(video.uploader_id)}
        )
        raise AuthorizationError("You can delete only your own videos")
    await video_service.delete_video(video)


@router.get("/{video_id}/results", response_model=list[VideoProcessingResultRead])
async def get_video_results(
    video_id: uuid.UUID,
    video_service: VideoService = Depends(get_video_service),
) -> list[VideoProcessingResultRead]:
    """Получает результаты обработки видео."""
    video = ensure_found(await video_service.get_video(video_id), "Video")
    return [VideoProcessingResultRead.model_validate(result) for result in video.processing_results]