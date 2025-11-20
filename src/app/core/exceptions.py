"""Кастомные исключения для приложения."""


class UnsupportedVideoTypeError(Exception):
    """Исключение при попытке загрузить неподдерживаемый тип видео."""
    pass


class CameraNotFoundError(Exception):
    """Исключение при отсутствии камеры."""
    pass


class MinioStorageError(Exception):
    """Исключение при ошибках работы с хранилищем."""
    pass


class UserAlreadyExistsError(Exception):
    """Исключение при попытке создать пользователя с существующим email."""
    pass

