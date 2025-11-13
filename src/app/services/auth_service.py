from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.config import settings
from src.app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from src.app.models import RefreshToken, User
from src.app.schemas import LoginRequest, TokenPair, UserCreate
from src.app.services.user_service import UserAlreadyExistsError, UserService


class AuthService:
    def __init__(self, session: AsyncSession, user_service: UserService):
        self._session = session
        self._user_service = user_service

    async def register_user(self, payload: UserCreate) -> User:
        try:
            return await self._user_service.create_user(payload)
        except UserAlreadyExistsError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    async def authenticate(self, login_data: LoginRequest) -> TokenPair:
        user = await self._user_service.get_by_email(login_data.email)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        return await self._issue_token_pair(user)

    async def refresh(self, refresh_token: str) -> TokenPair:
        hashed_token = hash_refresh_token(refresh_token)
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token == hashed_token)
            .where(RefreshToken.is_revoked.is_(False))
        )
        result = await self._session.execute(stmt)
        token_entry = result.scalar_one_or_none()

        if not token_entry:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        if token_entry.expires_at < datetime.now(timezone.utc):
            token_entry.is_revoked = True
            await self._session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired",
            )

        user = await self._user_service.get_by_id(token_entry.user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        token_entry.is_revoked = True
        await self._session.commit()

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




