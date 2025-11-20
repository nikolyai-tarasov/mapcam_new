"""Настройка логирования для приложения."""
import logging
import sys
from typing import Any

from pythonjsonlogger import jsonlogger


def setup_logging(log_level: str = "INFO") -> None:
    """
    Настраивает логирование с JSON форматом для production.
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger для модуля.
    
    Args:
        name: Имя модуля (обычно __name__)
    
    Returns:
        Настроенный logger
    """
    return logging.getLogger(name)


def log_extra(**kwargs: Any) -> dict[str, Any]:
    """
    Создать словарь для extra параметров логирования.
    
    Args:
        **kwargs: Дополнительные поля для логирования
    
    Returns:
        Словарь для передачи в extra параметр
    """
    return kwargs

