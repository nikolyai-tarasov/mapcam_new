from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.app.core.config import settings
from src.app.db.base import Base


class AsyncDataBaseSession:
    """Управляет жизненным циклом async SQLAlchemy engine и сессий."""

    def __init__(self) -> None:
        self.db_url = settings.database_url
        self.engine = create_async_engine(
            self.db_url,
            echo=settings.DEBUG,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "timeout": 10,
                "server_settings": {"statement_timeout": "30000"},
            },
        )
        self.AsyncSessionLocal = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    def get_session(self) -> AsyncSession:
        return self.AsyncSessionLocal()

    async def create_tables(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        await self.engine.dispose()


async_db_session = AsyncDataBaseSession()




