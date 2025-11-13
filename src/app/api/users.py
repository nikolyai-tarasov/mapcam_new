from fastapi import APIRouter, Depends

from src.app.api.dependencies import get_current_user, get_video_service
from src.app.models import User
from src.app.schemas import UserDashboard, VideoFilter, VideoRead
from src.app.services.video_service import VideoService


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/dashboard", response_model=UserDashboard)
async def get_user_dashboard(
    current_user: User = Depends(get_current_user),
    video_service: VideoService = Depends(get_video_service),
) -> UserDashboard:
    personal_filters = VideoFilter(uploader_email=current_user.email)
    recent_videos = await video_service.list_videos(personal_filters, limit=5)
    personal_total = await video_service.count_videos(personal_filters)
    public_total = await video_service.count_videos()

    return UserDashboard(
        user=current_user,
        recent_videos=[VideoRead.model_validate(video) for video in recent_videos],
        total_uploaded=personal_total,
        total_available=public_total,
    )




