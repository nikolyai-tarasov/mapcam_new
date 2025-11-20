"""Конфигурация логирования для приложения."""
import logging
import sys
from typing import Any

from src.app.core.config import settings


def setup_logging() -> None:
    """Настраивает общеприкладное логирование."""
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Получает экземпляр логгера для модуля."""
    return logging.getLogger(name)


class LoggerMixin:
    """Примесный класс для добавления логгера в любой класс."""

    @property
    def logger(self) -> logging.Logger:
        """Получает экземпляр логгера для этого класса."""
        return logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)