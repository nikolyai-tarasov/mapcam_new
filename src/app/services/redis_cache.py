from __future__ import annotations

import asyncio
import json
from typing import Any

from redis import asyncio as redis_asyncio

from src.app.core.config import settings


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
    async def get_json(cls, key: str) -> Any:
        client = await cls.get_client()
        raw = await client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
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
    async def acquire_lock(
        cls,
        lock_key: str,
        timeout: int = 30,
        expire_seconds: int = 60,
    ) -> bool:
        """
        Попытаться получить distributed lock.
        
        Args:
            lock_key: Ключ для lock
            timeout: Время ожидания в секундах
            expire_seconds: Время жизни lock в секундах
        
        Returns:
            True если lock получен, False иначе
        """
        client = await cls.get_client()
        lock_value = f"lock:{asyncio.current_task().get_name() if asyncio.current_task() else 'unknown'}"
        
        result = await client.set(lock_key, lock_value, nx=True, ex=expire_seconds)
        return result is True
    
    @classmethod
    async def release_lock(cls, lock_key: str) -> None:
        """
        Освободить distributed lock.
        
        Args:
            lock_key: Ключ для lock
        """
        client = await cls.get_client()
        await client.delete(lock_key)




