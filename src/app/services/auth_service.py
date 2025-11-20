from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.exceptions import UserAlreadyExistsError
from src.app.core.logging_config import get_logger, log_extra
from src.app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from src.app.models import RefreshToken, User
from src.app.schemas import LoginRequest, TokenPair, UserCreate
from src.app.services.user_service import UserService

logger = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession, user_service: UserService):
        self._session = session
        self._user_service = user_service

    async def register_user(self, payload: UserCreate) -> User:
        logger.info("Registering new user", extra=log_extra(email=payload.email))
        try:
            user = await self._user_service.create_user(payload)
            logger.info("User registered successfully", extra=log_extra(user_id=str(user.id)))
            return user
        except UserAlreadyExistsError as exc:
            logger.warning("User registration failed - already exists", extra=log_extra(email=payload.email))
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    async def authenticate(self, login_data: LoginRequest) -> TokenPair:
        logger.info("User authentication attempt", extra=log_extra(email=login_data.email))
        user = await self._user_service.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning("Authentication failed", extra=log_extra(email=login_data.email))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        logger.info("User authenticated successfully", extra=log_extra(user_id=str(user.id)))
        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """
        Обновить access token используя refresh token.
        
        Использует SELECT FOR UPDATE для предотвращения race condition
        при одновременном использовании одного refresh token.
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
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if token_entry.expires_at < datetime.now(timezone.utc):
            token_entry.is_revoked = True
            await self._session.commit()
            logger.warning("Expired refresh token used", extra=log_extra(token_id=str(token_entry.id)))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        user = await self._user_service.get_by_id(token_entry.user_id)
        if not user:
            logger.warning("User not found for refresh token", extra=log_extra(user_id=str(token_entry.user_id)))
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        token_entry.is_revoked = True
        await self._session.commit()
        
        logger.info("Refresh token used successfully", extra=log_extra(user_id=str(user.id)))
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




