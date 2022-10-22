class Error(Exception):
    """Базовый класс для кастомных исключений"""
    pass


class TelegramError(Error):
    """Ошибка телеграм-бота"""
    pass


class ConnectionError(Error):
    """Ошибка связи с сервером"""
    pass


class ObjectIsNoneError(Error):
    """Ошибка отсутствия имени или статуса работы"""
    pass
