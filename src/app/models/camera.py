from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.app.db.base import Base


class Camera(Base):
    __tablename__ = "d_camera"
    __table_args__ = (
        UniqueConstraint("camera_id", name="uq_camera_camera_id"),
        UniqueConstraint("serial_number", name="uq_camera_serial_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    camera_class_cd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    camera_class: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    camera_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    camera_place: Mapped[str | None] = mapped_column(Text, nullable=True)
    camera_place_cd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_type_cd: Mapped[int | None] = mapped_column(Integer, nullable=True)
    camera_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    camera_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    camera_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    archive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    azimuth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    process_dttm: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    videos: Mapped[list["Video"]] = relationship(
        "Video",
        back_populates="camera",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def geo_point(self) -> tuple[float, float] | None:
        if self.camera_longitude is None or self.camera_latitude is None:
            return None
        return self.camera_longitude, self.camera_latitude

    @property
    def has_video(self) -> bool:
        return any(video.is_active for video in self.videos)


if TYPE_CHECKING:
    from src.app.models.video import Video




