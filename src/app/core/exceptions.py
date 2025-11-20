"""Пользовательские исключения для приложения."""


class UnsupportedVideoTypeError(Exception):
    """Вызывается когда тип видеофайла не поддерживается."""
    pass


class CameraNotFoundError(Exception):
    """Вызывается когда камера не найдена."""
    pass


class UserAlreadyExistsError(Exception):
    """Вызывается когда пользователь уже существует."""
    pass


class VideoNotFoundError(Exception):
    """Вызывается когда видео не найдено."""
    pass


class StorageError(Exception):
    """Вызывается когда операция с хранилищем не удалась."""
    pass


class AuthenticationError(Exception):
    """Вызывается когда аутентификация не удалась."""
    pass


class AuthorizationError(Exception):
    """Вызывается когда пользователь не авторизован."""
    pass