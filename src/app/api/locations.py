from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from src.app.api.dependencies import get_location_service
from src.app.schemas import (
    LocationAnalyticsFilter,
    LocationAnalyticsResponse,
    LocationVideoFilter,
    LocationVideosResponse,
)
from src.app.services.location_service import CameraNotFound, LocationService


router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/{camera_id}/videos", response_model=LocationVideosResponse)
async def get_location_videos(
    camera_id: uuid.UUID,
    title: str | None = Query(default=None),
    uploader_email: str | None = Query(default=None),
    statuses: Annotated[list[str] | None, Query()] = None,
    processing_statuses: Annotated[list[str] | None, Query()] = None,
    uploaded_from: datetime | None = Query(default=None),
    uploaded_to: datetime | None = Query(default=None),
    location_service: LocationService = Depends(get_location_service),
) -> LocationVideosResponse:
    filters = LocationVideoFilter(
        title=title,
        uploader_email=uploader_email,
        statuses=statuses,
        processing_statuses=processing_statuses,
        uploaded_from=uploaded_from,
        uploaded_to=uploaded_to,
    )
    try:
        return await location_service.get_videos(camera_id, filters)
    except CameraNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{camera_id}/analytics", response_model=LocationAnalyticsResponse)
async def get_location_analytics(
    camera_id: uuid.UUID,
    analysis_type: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    video_id: uuid.UUID | None = Query(default=None),
    location_service: LocationService = Depends(get_location_service),
) -> LocationAnalyticsResponse:
    filters = LocationAnalyticsFilter(
        analysis_type=analysis_type,
        created_from=created_from,
        created_to=created_to,
        video_id=video_id,
    )
    try:
        return await location_service.get_analytics(camera_id, filters)
    except CameraNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc




