from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.exceptions import UserAlreadyExistsError
from src.app.core.logging_config import get_logger, log_extra
from src.app.core.security import hash_password
from src.app.models import User
from src.app.schemas.user import UserCreate

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_user(self, user_in: UserCreate) -> User:
        logger.info("Creating user", extra=log_extra(email=user_in.email))
        
        existing = await self.get_by_email(user_in.email)
        if existing:
            logger.warning("User creation failed - already exists", extra=log_extra(email=user_in.email))
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
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("User creation failed - integrity error", extra=log_extra(email=user_in.email, error=str(exc)))
            raise UserAlreadyExistsError("User with this email already exists.") from exc

        await self._session.refresh(user)
        logger.info("User created successfully", extra=log_extra(user_id=str(user.id), email=user_in.email))
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()




