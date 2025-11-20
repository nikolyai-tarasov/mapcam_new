from typing import TypeVar

from fastapi import HTTPException, status

T = TypeVar("T")


def ensure_found(entity: T | None, entity_name: str) -> T:
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found"
        )
    return entity
