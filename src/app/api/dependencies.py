from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.constants import AppConfig
from src.app.core.security import decode_token
from src.app.db.db_session import async_db_session
from src.app.models import User
from src.app.services.auth_service import AuthService
from src.app.services.camera_service import CameraService
from src.app.services.location_service import LocationService
from src.app.services.user_service import UserService
from src.app.services.video_service import VideoService


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{AppConfig.API_PREFIX}/auth/login")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_db_session.get_session() as session:
        yield session


def get_user_service(session: AsyncSession = Depends(get_db_session)) -> UserService:
    return UserService(session)


def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthService:
    user_service = UserService(session)
    return AuthService(session=session, user_service=user_service)


def get_camera_service(session: AsyncSession = Depends(get_db_session)) -> CameraService:
    return CameraService(session)


def get_video_service(session: AsyncSession = Depends(get_db_session)) -> VideoService:
    return VideoService(session)


def get_location_service(session: AsyncSession = Depends(get_db_session)) -> LocationService:
    return LocationService(session)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
    except ValueError as exc:
        raise credentials_exception from exc

    if payload.get("type") != "access":
        raise credentials_exception

    sub = payload.get("sub")
    if not sub:
        raise credentials_exception

    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError) as exc:
        raise credentials_exception from exc

    user = await user_service.get_by_id(user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user




