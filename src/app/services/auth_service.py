from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.exceptions import AuthenticationError
from src.app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from src.app.models import RefreshToken, User
from src.app.schemas import LoginRequest, TokenPair, UserCreate
from src.app.services.user_service import UserAlreadyExistsError, UserService

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession, user_service: UserService):
        self._session = session
        self._user_service = user_service

    async def register_user(self, payload: UserCreate) -> User:
        """Регистрирует нового пользователя."""
        logger.info("Registering user", extra={"email": payload.email})
        return await self._user_service.create_user(payload)

    async def authenticate(self, login_data: LoginRequest) -> TokenPair:
        """Аутентифицирует пользователя и выдает пару токенов."""
        logger.info("Authenticating user", extra={"email": login_data.email})
        user = await self._user_service.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning("Authentication failed", extra={"email": login_data.email})
            raise AuthenticationError("Incorrect email or password")

        logger.info("User authenticated successfully", extra={"user_id": str(user.id)})
        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """
        Обновляет access token с помощью refresh token.

        Использует SELECT FOR UPDATE для предотвращения состояний гонки
        при множественных запросах на обновление с одним токеном.
        """
        hashed_token = hash_refresh_token(refresh_token)

        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token == hashed_token)
            .where(RefreshToken.is_revoked.is_(False))
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        token_entry = result.scalar_one_or_none()

        if not token_entry:
            logger.warning("Invalid refresh token used")
            raise AuthenticationError("Invalid refresh token")

        now = datetime.now(timezone.utc)
        if token_entry.expires_at < now:
            token_entry.is_revoked = True
            await self._session.commit()
            logger.warning("Expired refresh token used", extra={"token_id": str(token_entry.id)})
            raise AuthenticationError("Refresh token expired")

        user = await self._user_service.get_by_id(token_entry.user_id)
        if not user:
            logger.warning("User not found for refresh token", extra={"user_id": str(token_entry.user_id)})
            raise AuthenticationError("User not found")

        token_entry.is_revoked = True
        await self._session.commit()
        logger.info("Refresh token revoked and new tokens issued", extra={"user_id": str(user.id)})

        return await self._issue_token_pair(user)

    async def _issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(str(user.id))
        refresh_token_raw = generate_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_entry = RefreshToken(
            user_id=user.id,
            token=hash_refresh_token(refresh_token_raw),
            expires_at=expires_at,
        )
        self._session.add(refresh_entry)
        await self._session.commit()

        return TokenPair(access_token=access_token, refresh_token=refresh_token_raw)