from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from src.app.api.router import api_router
from src.app.core.constants import AppConfig, CorsConfig
from src.app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CameraNotFoundError,
    StorageError,
    UnsupportedVideoTypeError,
    UserAlreadyExistsError,
    VideoNotFoundError,
)
from src.app.core.logging_config import setup_logging
from src.app.db.db_session import async_db_session
from src.app.models import Camera
from src.app.services.camera_service import CameraService
from src.app.services.redis_cache import RedisCache
from src.app.services.storage_service import minio_storage
from src.app.services.video_processing_queue import video_processing_queue
from src.app.services import video_processing_service

setup_logging()


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


def configure_exception_handlers(application: FastAPI) -> None:
    """Настраивает обработчики исключений для приложения."""

    @application.exception_handler(UnsupportedVideoTypeError)
    async def unsupported_video_type_handler(request: Request, exc: UnsupportedVideoTypeError):
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": str(exc)}
        )

    @application.exception_handler(CameraNotFoundError)
    async def camera_not_found_handler(request: Request, exc: CameraNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)}
        )

    @application.exception_handler(VideoNotFoundError)
    async def video_not_found_handler(request: Request, exc: VideoNotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)}
        )

    @application.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)}
        )

    @application.exception_handler(StorageError)
    async def storage_error_handler(request: Request, exc: StorageError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Storage operation failed"}
        )

    @application.exception_handler(AuthenticationError)
    async def authentication_error_handler(request: Request, exc: AuthenticationError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)}
        )

    @application.exception_handler(AuthorizationError)
    async def authorization_error_handler(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)}
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()}
        )


def configure_middleware(application: FastAPI) -> None:
    """Настраивает middleware для приложения."""
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
    """Создает и настраивает FastAPI приложение."""
    application = FastAPI(
        title=AppConfig.TITLE,
        description=AppConfig.DESCRIPTION,
        version=get_app_version(),
        lifespan=lifespan,
    )
    configure_exception_handlers(application)
    configure_middleware(application)
    register_routes(application)
    return application


app = create_application()