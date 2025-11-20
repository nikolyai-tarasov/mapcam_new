from fastapi import APIRouter, Depends, Request, status

from src.app.api.dependencies import get_auth_service, get_current_user
from src.app.core.constants import RateLimitConfig
from src.app.core.rate_limiting import limiter
from src.app.models import User
from src.app.schemas import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from src.app.services.auth_service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit(RateLimitConfig.REGISTER_LIMIT)
async def register_user(
    request: Request,
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    return await auth_service.register_user(user_data)


@router.post("/login", response_model=TokenPair)
@limiter.limit(RateLimitConfig.LOGIN_LIMIT)
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await auth_service.authenticate(login_data)


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    request: RefreshRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenPair:
    return await auth_service.refresh(request.refresh_token)


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user




