from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import UserAlreadyExistsError
from src.app.core.security import hash_password
from src.app.models import User
from src.app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, user_in: UserCreate) -> User:
        """Создает нового пользователя."""
        logger.info("Creating user", extra={"email": user_in.email})
        existing = await self.get_by_email(user_in.email)
        if existing:
            logger.warning("User already exists", extra={"email": user_in.email})
            raise UserAlreadyExistsError("User with this email already exists.")

        user = User(
            email=user_in.email.lower(),
            full_name=user_in.full_name,
            organization=user_in.organization,
            hashed_password=hash_password(user_in.password),
        )
        self._session.add(user)
        try:
            await self._session.commit()
            logger.info("User created successfully", extra={"user_id": str(user.id), "email": user_in.email})
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("User creation failed due to integrity error", extra={"email": user_in.email})
            raise UserAlreadyExistsError("User with this email already exists.") from exc

        await self._session.refresh(user)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()