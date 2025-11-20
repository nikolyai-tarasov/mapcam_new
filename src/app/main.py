from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import func, select

from src.app.core.rate_limiting import limiter

from src.app.api.router import api_router
from src.app.core.config import settings
from src.app.core.constants import AppConfig, CorsConfig
from src.app.core.exceptions import (
    CameraNotFoundError,
    MinioStorageError,
    UnsupportedVideoTypeError,
    UserAlreadyExistsError,
)
from src.app.core.logging_config import get_logger, setup_logging
from src.app.db.db_session import async_db_session
from src.app.models import Camera
from src.app.services.camera_service import CameraService
from src.app.services.redis_cache import RedisCache
from src.app.services.storage_service import minio_storage
from src.app.services.video_processing_queue import video_processing_queue
from src.app.services import video_processing_service

logger = get_logger(__name__)


def get_app_version() -> str:
    try:
        return version("mapcam-new")
    except PackageNotFoundError:
        return AppConfig.VERSION_FALLBACK


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup", extra={"version": get_app_version()})
    
    try:
        await async_db_session.create_tables()
        logger.info("Database tables created/verified")
        
        await minio_storage.ensure_bucket()
        logger.info("MinIO bucket ensured")
        
        await video_processing_queue.start()
        logger.info("Video processing queue started")

        async with async_db_session.get_session() as session:
            result = await session.execute(select(func.count(Camera.id)))
            if result.scalar_one() == 0:
                logger.info("Seeding random cameras")
                service = CameraService(session)
                await service.seed_random_cameras()
                logger.info("Random cameras seeded")
    except Exception as exc:
        logger.exception("Error during application startup", extra={"error": str(exc)})
        raise

    try:
        yield
    finally:
        logger.info("Application shutdown started")
        try:
            await video_processing_queue.stop()
            logger.info("Video processing queue stopped")
        except Exception as exc:
            logger.exception("Error stopping video processing queue", extra={"error": str(exc)})
        
        try:
            await RedisCache.close()
            logger.info("Redis connection closed")
        except Exception as exc:
            logger.exception("Error closing Redis connection", extra={"error": str(exc)})
        
        try:
            await async_db_session.close()
            logger.info("Database session closed")
        except Exception as exc:
            logger.exception("Error closing database session", extra={"error": str(exc)})
        
        logger.info("Application shutdown completed")


def configure_middleware(application: FastAPI) -> None:
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    application.add_middleware(SlowAPIMiddleware)
    
    allowed_origins = CorsConfig.ALLOW_ORIGINS
    if allowed_origins == ["*"] and CorsConfig.ALLOW_CREDENTIALS:
        logger.warning(
            "CORS allow_origins=['*'] with allow_credentials=True is insecure. "
            "Consider specifying exact origins in production."
        )
    
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=CorsConfig.ALLOW_CREDENTIALS,
        allow_methods=CorsConfig.ALLOW_METHODS,
        allow_headers=CorsConfig.ALLOW_HEADERS,
    )
    
    if settings.DEBUG:
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    else:
        logger.warning("TrustedHostMiddleware with allowed_hosts=['*'] is insecure in production")
        application.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])


def register_exception_handlers(application: FastAPI) -> None:
    """Регистрирует централизованные обработчики исключений."""
    
    @application.exception_handler(UnsupportedVideoTypeError)
    async def unsupported_video_type_handler(request: Request, exc: UnsupportedVideoTypeError):
        logger.warning(
            "Unsupported video type",
            extra={"path": request.url.path, "error": str(exc)}
        )
        return JSONResponse(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            content={"detail": str(exc)}
        )
    
    @application.exception_handler(CameraNotFoundError)
    async def camera_not_found_handler(request: Request, exc: CameraNotFoundError):
        logger.warning(
            "Camera not found",
            extra={"path": request.url.path, "error": str(exc)}
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)}
        )
    
    @application.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_handler(request: Request, exc: UserAlreadyExistsError):
        logger.warning(
            "User already exists",
            extra={"path": request.url.path, "error": str(exc)}
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": str(exc)}
        )
    
    @application.exception_handler(MinioStorageError)
    async def minio_storage_error_handler(request: Request, exc: MinioStorageError):
        logger.error(
            "MinIO storage error",
            extra={"path": request.url.path, "error": str(exc)},
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Storage operation failed"}
        )


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
    setup_logging(settings.LOG_LEVEL)
    
    application = FastAPI(
        title=AppConfig.TITLE,
        description=AppConfig.DESCRIPTION,
        version=get_app_version(),
        lifespan=lifespan,
    )
    configure_middleware(application)
    register_exception_handlers(application)
    register_routes(application)
    return application


app = create_application()





