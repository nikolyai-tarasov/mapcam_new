class AppConfig:
    TITLE = "MapCam Video Intelligence"
    DESCRIPTION = (
        "Сервис авторизации пользователей и управления видеоматериалами, "
        "привязанными к городским камерам наблюдения."
    )
    VERSION_FALLBACK = "0.1.0"
    API_PREFIX = "/api/v1"


class CorsConfig:
    ALLOW_ORIGINS = ["*"]
    ALLOW_METHODS = ["*"]
    ALLOW_HEADERS = ["*"]
    ALLOW_CREDENTIALS = True


class SecurityConfig:
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7


class CacheConfig:
    """Конфигурация кэширования."""
    GEOJSON_TTL_SECONDS = 300
    VIDEO_METADATA_TTL_SECONDS = 1800
    LOCK_TIMEOUT_SECONDS = 30


class StorageConfig:
    """Конфигурация хранилища."""
    PRESIGNED_URL_EXPIRE_SECONDS = 3600
    UPLOAD_CHUNK_SIZE = 10 * 1024 * 1024
    MAX_VIDEO_SIZE = 500 * 1024 * 1024


class RateLimitConfig:
    """Конфигурация ограничения запросов."""
    REGISTER_LIMIT = "5/hour"
    UPLOAD_LIMIT = "10/hour"
    LOGIN_LIMIT = "10/minute"
    GENERAL_LIMIT = "100/hour"