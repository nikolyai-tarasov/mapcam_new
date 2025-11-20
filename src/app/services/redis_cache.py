from __future__ import annotations

import asyncio
import json
from typing import Any, TypeVar

from redis import asyncio as redis_asyncio

from src.app.core.config import settings

T = TypeVar("T")


class RedisCache:
    """Легковесная обертка над Redis для хранения JSON-совместимых структур."""

    _client: redis_asyncio.Redis | None = None

    @classmethod
    async def get_client(cls) -> redis_asyncio.Redis:
        if cls._client is None:
            cls._client = redis_asyncio.Redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None:
            await cls._client.close()
            cls._client = None

    @classmethod
    async def get_json(cls, key: str) -> dict[str, Any] | list[Any] | None:
        """
        Получает JSON значение из кэша.

        Returns:
            Распарсенное JSON значение (dict или list) или None если не найдено/невалидно
        """
        client = await cls.get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, (dict, list)):
                return parsed
            return None
        except json.JSONDecodeError:
            return None

    @classmethod
    async def set_json(cls, key: str, value: Any, expire_seconds: int | None = None) -> None:
        client = await cls.get_client()
        data = json.dumps(value, ensure_ascii=False)
        if expire_seconds:
            await client.set(key, data, ex=expire_seconds)
        else:
            await client.set(key, data)

    @classmethod
    async def delete(cls, key: str) -> None:
        client = await cls.get_client()
        await client.delete(key)

    @classmethod
    async def acquire_lock(cls, key: str, timeout: int = 30) -> bool:
        """
        Получает распределенную блокировку.

        Args:
            key: Ключ блокировки
            timeout: Таймаут блокировки в секундах

        Returns:
            True если блокировка получена, False в противном случае
        """
        client = await cls.get_client()
        lock_key = f"{key}:lock"
        result = await client.set(lock_key, "1", ex=timeout, nx=True)
        return result is True

    @classmethod
    async def release_lock(cls, key: str) -> None:
        """Освобождает распределенную блокировку."""
        client = await cls.get_client()
        lock_key = f"{key}:lock"
        await client.delete(lock_key)

    @classmethod
    async def lock_context(cls, key: str, timeout: int = 30):
        """
        Контекстный менеджер для распределенной блокировки.

        Usage:
            async with RedisCache.lock_context("my_key"):
                # Критическая секция
                pass
        """

        class LockContext:
            def __init__(self, cache_cls, lock_key: str, timeout: int):
                self.cache_cls = cache_cls
                self.lock_key = lock_key
                self.timeout