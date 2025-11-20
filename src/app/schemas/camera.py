from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CameraBase(BaseModel):
    camera_id: str = Field(..., max_length=128)
    camera_class_cd: int | None = None
    camera_class: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=255)
    camera_name: str | None = Field(default=None, max_length=255)
    camera_place: str | None = None
    camera_place_cd: int | None = None
    serial_number: str | None = Field(default=None, max_length=128)
    camera_type_cd: int | None = None
    camera_type: str | None = Field(default=None, max_length=128)
    camera_latitude: float | None = None
    camera_longitude: float | None = None
    archive: bool = False
    azimuth: int | None = None


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    camera_class_cd: int | None = None
    camera_class: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=255)
    camera_name: str | None = Field(default=None, max_length=255)
    camera_place: str | None = None
    camera_place_cd: int | None = None
    serial_number: str | None = Field(default=None, max_length=128)
    camera_type_cd: int | None = None
    camera_type: str | None = Field(default=None, max_length=128)
    camera_latitude: float | None = None
    camera_longitude: float | None = None
    archive: bool | None = None
    azimuth: int | None = None


class CameraRead(CameraBase):
    id: uuid.UUID
    process_dttm: datetime
    created_at: datetime
    updated_at: datetime
    has_video: bool

    model_config = {"from_attributes": True}


class CameraGeoJsonFeatureProperties(BaseModel):
    camera_id: str
    has_video: bool
    camera_name: str | None = None
    camera_type: str | None = None
    camera_class: str | None = None


class CameraGeoJsonFeature(BaseModel):
    type: str = "Feature"
    properties: CameraGeoJsonFeatureProperties
    geometry: dict[str, Any]


class CameraGeoJsonCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[CameraGeoJsonFeature]


class CameraFilter(BaseModel):
    query: str | None = Field(default=None)
    models: list[str] | None = Field(default=None)
    types: list[str] | None = Field(default=None)
    classes: list[str] | None = Field(default=None)
    min_videos: int | None = Field(default=None, ge=0)
    max_videos: int | None = Field(default=None, ge=0)
    has_video: bool | None = Field(default=None)




