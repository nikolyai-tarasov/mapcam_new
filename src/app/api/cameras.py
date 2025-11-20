from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.app.api.dependencies import get_camera_service, get_video_service
from src.app.schemas import CameraFilter, CameraGeoJsonCollection, CameraRead
from src.app.services.camera_service import CameraService
from src.app.services.video_service import VideoService


router = APIRouter(prefix="/cameras", tags=["cameras"])


@router.get("/", response_model=list[CameraRead])
async def list_cameras(
    query: str | None = Query(default=None, description="Поиск по названию/адресу/идентификатору"),
    models: Annotated[list[str] | None, Query()] = None,
    types: Annotated[list[str] | None, Query()] = None,
    classes: Annotated[list[str] | None, Query()] = None,
    min_videos: int | None = Query(default=None, ge=0),
    max_videos: int | None = Query(default=None, ge=0),
    has_video: bool | None = Query(default=None),
    camera_service: CameraService = Depends(get_camera_service),
) -> list[CameraRead]:
    filters = CameraFilter(
        query=query,
        models=models,
        types=types,
        classes=classes,
        min_videos=min_videos,
        max_videos=max_videos,
        has_video=has_video,
    )
    cameras = await camera_service.list_cameras(filters)
    return [CameraRead.model_validate(camera) for camera in cameras]


@router.get("/geojson", response_model=CameraGeoJsonCollection)
async def get_geojson(
    camera_service: CameraService = Depends(get_camera_service),
) -> CameraGeoJsonCollection:
    return await camera_service.get_geojson()


@router.post("/seed", response_model=list[CameraRead])
async def seed_cameras(
    count: int = Query(default=25, ge=1, le=500),
    camera_service: CameraService = Depends(get_camera_service),
) -> list[CameraRead]:
    return await camera_service.seed_random_cameras(count)


@router.post(
    "/{camera_id}/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def attach_video_to_camera(
    camera_id: uuid.UUID,
    video_id: uuid.UUID,
    camera_service: CameraService = Depends(get_camera_service),
    video_service: VideoService = Depends(get_video_service),
) -> None:
    camera = await camera_service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    video = await video_service.get_video(video_id)
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    await camera_service.attach_video(camera, video)


@router.delete(
    "/{camera_id}/videos/{video_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_video_from_camera(
    camera_id: uuid.UUID,
    video_id: uuid.UUID,
    camera_service: CameraService = Depends(get_camera_service),
    video_service: VideoService = Depends(get_video_service),
) -> None:
    camera = await camera_service.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found")

    video = await video_service.get_video(video_id)
    if not video or video.camera_id != camera_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not attached to camera")

    await camera_service.detach_video(video)




