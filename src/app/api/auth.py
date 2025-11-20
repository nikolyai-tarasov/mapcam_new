import logging

from fastapi import APIRouter, Depends, status

from src.app.api.dependencies import get_auth_service, get_current_user
from src.app.models import User
from src.app.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from src.app.services.auth_service import AuthService

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Регистрирует нового пользователя."""
    logger.info("User registration request", extra={"email": user_data.email})
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=TokenPair)
async def login(
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Аутентифицирует пользователя и возвращает пару токенов."""
    logger.info("User login request", extra={"email": login_data.email})
    return await auth_service.authenticate(login_data)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    """Обновляет access token с помощью refresh token."""
    logger.debug("Token refresh request")
    return await auth_service.refresh(request.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user