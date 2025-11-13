from fastapi import APIRouter

from src.app.api import auth, cameras, locations, users, videos

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(cameras.router)
api_router.include_router(videos.router)
api_router.include_router(locations.router)




