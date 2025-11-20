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




