from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from src.app.core.constants import CacheConfig
from src.app.core.logging_config import get_logger, log_extra
from src.app.models import Camera, Video
from src.app.schemas import (
    CameraFilter,
    CameraGeoJsonCollection,
    CameraGeoJsonFeature,
    CameraGeoJsonFeatureProperties,
    CameraRead,
)
from src.app.services.redis_cache import RedisCache

logger = get_logger(__name__)
CAMERA_GEOJSON_CACHE_KEY = "mapcam:geojson:cameras"
CAMERA_GEOJSON_LOCK_KEY = "mapcam:geojson:cameras:lock"


class CameraService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_cameras(self, camera_filter: CameraFilter | None = None) -> list[Camera]:
        stmt = self._build_camera_query(camera_filter)
        result = await self._session.execute(stmt.options(joinedload(Camera.videos)))
        return list(result.scalars().unique())

    async def get_camera(self, camera_id: uuid.UUID) -> Camera | None:
        stmt = select(Camera).where(Camera.id == camera_id).options(joinedload(Camera.videos))
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_geojson(
        self,
        camera_filter: CameraFilter | None = None,
        use_cache: bool = True,
    ) -> CameraGeoJsonCollection:
        """
        Получить GeoJSON коллекцию камер с защитой от cache stampede.
        
        Использует distributed lock для предотвращения одновременного вычисления
        кэша несколькими workers.
        """
        if use_cache and not camera_filter:
            cached = await RedisCache.get_json(CAMERA_GEOJSON_CACHE_KEY)
            if cached:
                logger.debug("GeoJSON cache hit")
                return CameraGeoJsonCollection.model_validate(cached)
            
            lock_acquired = await RedisCache.acquire_lock(
                CAMERA_GEOJSON_LOCK_KEY,
                timeout=30,
                expire_seconds=60
            )
            
            if lock_acquired:
                try:
                    cached = await RedisCache.get_json(CAMERA_GEOJSON_CACHE_KEY)
                    if cached:
                        logger.debug("GeoJSON cache hit after lock acquisition")
                        return CameraGeoJsonCollection.model_validate(cached)
                    
                    logger.info("Computing GeoJSON (cache miss, lock acquired)")
                    cameras = await self.list_cameras(camera_filter)
                    collection = self._to_geojson(cameras)
                    
                    await RedisCache.set_json(
                        CAMERA_GEOJSON_CACHE_KEY,
                        collection.model_dump(mode="json"),
                        expire_seconds=CacheConfig.GEOJSON_TTL_SECONDS
                    )
                    return collection
                finally:
                    await RedisCache.release_lock(CAMERA_GEOJSON_LOCK_KEY)
            else:
                logger.debug("Lock not acquired, waiting for cache")
                import asyncio
                await asyncio.sleep(0.5)
                cached = await RedisCache.get_json(CAMERA_GEOJSON_CACHE_KEY)
                if cached:
                    return CameraGeoJsonCollection.model_validate(cached)
                logger.warning("Computing GeoJSON without cache (lock timeout)")

        cameras = await self.list_cameras(camera_filter)
        collection = self._to_geojson(cameras)
        return collection

    async def invalidate_geojson_cache(self) -> None:
        await RedisCache.delete(CAMERA_GEOJSON_CACHE_KEY)

    async def attach_video(self, camera: Camera, video: Video) -> None:
        video.camera = camera
        await self._session.flush()
        await self.invalidate_geojson_cache()

    async def detach_video(self, video: Video) -> None:
        video.camera = None
        await self._session.flush()
        await self.invalidate_geojson_cache()

    def _build_camera_query(self, camera_filter: CameraFilter | None) -> Select[tuple[Camera]]:
        stmt = select(Camera).options(joinedload(Camera.videos))

        if not camera_filter:
            return stmt.order_by(Camera.camera_name.asc().nulls_last())

        if camera_filter.query:
            pattern = f"%{camera_filter.query.lower()}%"
            stmt = stmt.where(
                func.lower(Camera.camera_name).like(pattern)
                | func.lower(Camera.camera_place).like(pattern)
                | func.lower(Camera.camera_id).like(pattern)
            )
        if camera_filter.models:
            stmt = stmt.where(Camera.model.in_(camera_filter.models))
        if camera_filter.types:
            stmt = stmt.where(Camera.camera_type.in_(camera_filter.types))
        if camera_filter.classes:
            stmt = stmt.where(Camera.camera_class.in_(camera_filter.classes))
        if camera_filter.has_video is not None:
            stmt = stmt.where(Camera.archive.is_(False))
            stmt = stmt.join(Video, isouter=True)
            if camera_filter.has_video:
                stmt = stmt.where(Video.id.is_not(None))
            else:
                stmt = stmt.where(Video.id.is_(None))
        if camera_filter.min_videos is not None or camera_filter.max_videos is not None:
            stmt = stmt.outerjoin(Video).group_by(Camera.id)
            if camera_filter.min_videos is not None:
                stmt = stmt.having(func.count(Video.id) >= camera_filter.min_videos)
            if camera_filter.max_videos is not None:
                stmt = stmt.having(func.count(Video.id) <= camera_filter.max_videos)

        return stmt.order_by(Camera.camera_name.asc().nulls_last())

    def _to_geojson(self, cameras: Sequence[Camera]) -> CameraGeoJsonCollection:
        features: list[CameraGeoJsonFeature] = []
        for camera in cameras:
            point = camera.geo_point()
            if not point:
                continue
            properties = CameraGeoJsonFeatureProperties(
                camera_id=camera.camera_id,
                has_video=camera.has_video,
                camera_name=camera.camera_name,
                camera_type=camera.camera_type,
                camera_class=camera.camera_class,
            )
            geometry = {
                "type": "Point",
                "coordinates": list(point),
            }
            features.append(CameraGeoJsonFeature(properties=properties, geometry=geometry))
        return CameraGeoJsonCollection(features=features)

    async def seed_random_cameras(self, count: int = 25) -> list[CameraRead]:
        logger.info("Seeding random cameras", extra=log_extra(count=count))
        seeded: list[CameraRead] = []
        for _ in range(count):
            camera = Camera(
                camera_id=f"{random.randint(1, 99999):05d}",
                camera_class_cd=random.randint(1, 10),
                camera_class=random.choice(["A", "B", "C", "D"]),
                model=random.choice(["Axis Q1798", "Dahua IPC-HFW5541E", "Hikvision DS-2CD"]),
                camera_name=f"Camera #{random.randint(1, 200)}",
                camera_place=f"{random.randint(1, 200)} Lenina St",
                serial_number=str(uuid.uuid4())[:12],
                camera_type_cd=random.randint(1, 5),
                camera_type=random.choice(["Static", "PTZ", "Fisheye"]),
                camera_latitude=55.0 + random.random(),
                camera_longitude=37.0 + random.random(),
                archive=False,
                azimuth=random.randint(0, 360),
                process_dttm=datetime.now(timezone.utc),
            )
            self._session.add(camera)
            await self._session.flush()
            # Загружаем камеру заново с videos через selectinload, чтобы свойство has_video работало корректно
            camera_id = camera.id
            stmt = select(Camera).where(Camera.id == camera_id).options(selectinload(Camera.videos))
            result = await self._session.execute(stmt)
            camera_with_videos = result.scalar_one()
            seeded.append(CameraRead.model_validate(camera_with_videos))

        await self._session.commit()
        await self.invalidate_geojson_cache()
        logger.info("Random cameras seeded successfully", extra=log_extra(count=len(seeded)))
        return seeded




