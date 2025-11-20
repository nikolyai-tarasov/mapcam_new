from __future__ import annotations

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




