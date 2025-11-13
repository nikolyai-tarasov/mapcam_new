from src.app.schemas.auth import LoginRequest, RefreshRequest, TokenPair
from src.app.schemas.camera import (
    CameraCreate,
    CameraFilter,
    CameraGeoJsonCollection,
    CameraGeoJsonFeature,
    CameraGeoJsonFeatureProperties,
    CameraRead,
    CameraUpdate,
)
from src.app.schemas.dashboard import UserDashboard
from src.app.schemas.location import (
    LocationAnalyticsFilter,
    LocationAnalyticsResponse,
    LocationVideoFilter,
    LocationVideosResponse,
)
from src.app.schemas.user import UserCreate, UserRead
from src.app.schemas.video import (
    VideoCreate,
    VideoFilter,
    VideoProcessingResultFilter,
    VideoProcessingResultRead,
    VideoRead,
    VideoUploadRequest,
)

__all__ = [
    "LoginRequest",
    "RefreshRequest",
    "TokenPair",
    "UserCreate",
    "UserRead",
    "CameraCreate",
    "CameraUpdate",
    "CameraRead",
    "CameraFilter",
    "CameraGeoJsonFeatureProperties",
    "CameraGeoJsonFeature",
    "CameraGeoJsonCollection",
    "UserDashboard",
    "LocationVideoFilter",
    "LocationVideosResponse",
    "LocationAnalyticsFilter",
    "LocationAnalyticsResponse",
    "VideoCreate",
    "VideoRead",
    "VideoFilter",
    "VideoProcessingResultRead",
    "VideoProcessingResultFilter",
    "VideoUploadRequest",
]




