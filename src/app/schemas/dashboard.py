from pydantic import BaseModel

from src.app.schemas.user import UserRead
from src.app.schemas.video import VideoRead


class UserDashboard(BaseModel):
    user: UserRead
    recent_videos: list[VideoRead]
    total_uploaded: int
    total_available: int




