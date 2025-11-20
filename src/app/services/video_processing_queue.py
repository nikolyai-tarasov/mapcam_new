from __future__ import annotations

import asyncio
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VideoProcessingJob:
    video_id: uuid.UUID
    user_id: uuid.UUID | None


class VideoProcessingQueue:
    """Организует последовательную обработку видео для каждого пользователя."""

    def __init__(self, processor: Callable[[uuid.UUID], Awaitable[None]]) -> None:
        self._processor = processor
        self._queue: asyncio.Queue[VideoProcessingJob] = asyncio.Queue()
        self._user_locks: defaultdict[uuid.UUID | None, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._worker_task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    def set_processor(self, processor: Callable[[uuid.UUID], Awaitable[None]]) -> None:
        self._processor = processor

    async def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stopped.clear()
        self._worker_task = asyncio.create_task(self._worker(), name="video-processing-worker")

    async def stop(self) -> None:
        self._stopped.set()
        if self._worker_task:
            await self._queue.put(VideoProcessingJob(video_id=uuid.uuid4(), user_id=None))  # sentinel
            await self._worker_task
            self._worker_task = None

    async def enqueue(self, video_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
        await self._queue.put(VideoProcessingJob(video_id=video_id, user_id=user_id))

    async def _worker(self) -> None:
        while not self._stopped.is_set():
            job = await self._queue.get()
            if self._stopped.is_set():
                self._queue.task_done()
                break

            lock = self._user_locks[job.user_id]
            async with lock:
                try:
                    await self._processor(job.video_id)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Video processing for %s failed: %s", job.video_id, exc)
                finally:
                    self._queue.task_done()


async def _noop_processor(video_id: uuid.UUID) -> None:
    logger.debug("No-op processor invoked for video %s", video_id)


video_processing_queue = VideoProcessingQueue(_noop_processor)




