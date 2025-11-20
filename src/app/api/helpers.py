"""Helper функции для уменьшения дублирования кода в API endpoints."""
from typing import TypeVar

from fastapi import HTTPException, status

T = TypeVar("T")


def ensure_found(entity: T | None, entity_name: str) -> T:
    """
    Проверяет, что сущность найдена, иначе выбрасывает HTTPException.
    
    Args:
        entity: Сущность или None
        entity_name: Имя сущности для сообщения об ошибке
    
    Returns:
        Сущность, если она не None
    
    Raises:
        HTTPException: Если сущность None
    """
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_name} not found"
        )
    return entity

