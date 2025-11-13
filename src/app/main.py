from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, select

from src.app.api.router import api_router
from src.app.core.constants import AppConfig, CorsConfig
from src.app.db.db_session import async_db_session
from src.app.models import Camera
from src.app.services.camera_service import CameraService
from src.app.services.redis_cache import RedisCache
from src.app.services.storage_service import minio_storage
from src.app.services.video_processing_queue import video_processing_queue
from src.app.services import video_processing_service


def get_app_version() -> str:
    try:
        return version("mapcam-new")
    except PackageNotFoundError:
        return AppConfig.VERSION_FALLBACK


@asynccontextmanager
async def lifespan(app: FastAPI):
    await async_db_session.create_tables()
    await minio_storage.ensure_bucket()
    await video_processing_queue.start()

    async with async_db_session.get_session() as session:
        result = await session.execute(select(func.count(Camera.id)))
        if result.scalar_one() == 0:
            service = CameraService(session)
            await service.seed_random_cameras()

    try:
        yield
    finally:
        await video_processing_queue.stop()
        await RedisCache.close()
        await async_db_session.close()


def configure_middleware(application: FastAPI) -> None:
    application.add_middleware(
        CORSMiddleware,
        allow_origins=CorsConfig.ALLOW_ORIGINS,
        allow_credentials=CorsConfig.ALLOW_CREDENTIALS,
        allow_methods=CorsConfig.ALLOW_METHODS,
        allow_headers=CorsConfig.ALLOW_HEADERS,
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


def register_routes(application: FastAPI) -> None:
    application.include_router(api_router, prefix=AppConfig.API_PREFIX)

    @application.get("/")
    async def root():
        return {
            "message": "MapCam API",
            "version": application.version,
            "docs": "/docs",
            "redoc": "/redoc",
        }


def create_application() -> FastAPI:
    application = FastAPI(
        title=AppConfig.TITLE,
        description=AppConfig.DESCRIPTION,
        version=get_app_version(),
        lifespan=lifespan,
    )
    configure_middleware(application)
    register_routes(application)
    return application


app = create_application()





