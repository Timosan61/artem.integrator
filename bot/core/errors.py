"""
Централизованная обработка ошибок
"""

import sys
import traceback
from typing import Type, Optional, Dict, Any, Callable, Union
from functools import wraps
import asyncio
import logging
from datetime import datetime

from .logging import get_logger

logger = get_logger(__name__)


class BotError(Exception):
    """Базовый класс для ошибок бота"""
    
    def __init__(self, message: str, user_message: Optional[str] = None, **kwargs):
        """
        Args:
            message: Техническое сообщение об ошибке
            user_message: Сообщение для пользователя
            **kwargs: Дополнительный контекст
        """
        super().__init__(message)
        self.user_message = user_message or "Произошла ошибка. Попробуйте позже."
        self.context = kwargs
        self.timestamp = datetime.now()


class ConfigurationError(BotError):
    """Ошибка конфигурации"""
    pass


class ServiceError(BotError):
    """Ошибка сервиса"""
    
    def __init__(self, service: str, message: str, **kwargs):
        super().__init__(f"[{service}] {message}", **kwargs)
        self.service = service


class APIError(ServiceError):
    """Ошибка внешнего API"""
    
    def __init__(self, service: str, status_code: Optional[int] = None, 
                 response: Optional[str] = None, **kwargs):
        message = f"API error"
        if status_code:
            message += f" (status: {status_code})"
        
        super().__init__(service, message, **kwargs)
        self.status_code = status_code
        self.response = response


class ValidationError(BotError):
    """Ошибка валидации данных"""
    
    def __init__(self, field: str, value: Any, message: str, **kwargs):
        super().__init__(
            f"Validation error for '{field}': {message}",
            user_message=f"Некорректное значение в поле '{field}'",
            **kwargs
        )
        self.field = field
        self.value = value


class AuthorizationError(BotError):
    """Ошибка авторизации"""
    
    def __init__(self, user_id: Optional[int] = None, action: Optional[str] = None, **kwargs):
        message = "Authorization failed"
        if action:
            message += f" for action '{action}'"
        
        super().__init__(
            message,
            user_message="У вас нет прав для выполнения этого действия",
            **kwargs
        )
        self.user_id = user_id
        self.action = action


class RateLimitError(BotError):
    """Превышен лимит запросов"""
    
    def __init__(self, limit: int, window: int, **kwargs):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window} seconds",
            user_message=f"Превышен лимит запросов. Подождите {window} секунд",
            **kwargs
        )
        self.limit = limit
        self.window = window


class ErrorHandler:
    """
    Централизованный обработчик ошибок
    """
    
    _handlers: Dict[Type[Exception], Callable] = {}
    
    @classmethod
    def register(cls, error_type: Type[Exception], handler: Callable):
        """Регистрирует обработчик для типа ошибки"""
        cls._handlers[error_type] = handler
    
    @classmethod
    def handle(cls, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Обрабатывает ошибку и возвращает сообщение для пользователя
        
        Args:
            error: Исключение
            context: Дополнительный контекст
            
        Returns:
            str: Сообщение для пользователя
        """
        # Логируем ошибку
        extra = {"error_type": type(error).__name__}
        if context:
            extra.update(context)
        
        if isinstance(error, BotError):
            extra.update(error.context)
            logger.error(f"{error}", extra=extra, exc_info=True)
            return error.user_message
        else:
            logger.error(f"Unhandled error: {error}", extra=extra, exc_info=True)
        
        # Ищем специфичный обработчик
        for error_type, handler in cls._handlers.items():
            if isinstance(error, error_type):
                return handler(error, context)
        
        # Дефолтное сообщение
        return "Произошла непредвиденная ошибка. Администраторы уже уведомлены."
    
    @classmethod
    def format_traceback(cls, exc_info: Optional[tuple] = None) -> str:
        """Форматирует traceback для логирования"""
        if exc_info is None:
            exc_info = sys.exc_info()
        
        return ''.join(traceback.format_exception(*exc_info))


def error_handler(
    user_message: str = "Произошла ошибка", 
    log_level: int = logging.ERROR,
    reraise: bool = False
):
    """
    Декоратор для обработки ошибок в функциях
    
    Args:
        user_message: Сообщение для пользователя
        log_level: Уровень логирования
        reraise: Пробрасывать ли исключение дальше
    """
    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.log(
                    log_level,
                    f"Error in {func.__name__}: {e}",
                    extra={"function": func.__name__},
                    exc_info=True
                )
                
                if reraise:
                    raise
                
                if isinstance(e, BotError):
                    return {"error": e.user_message}
                else:
                    return {"error": user_message}
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.log(
                    log_level,
                    f"Error in {func.__name__}: {e}",
                    extra={"function": func.__name__},
                    exc_info=True
                )
                
                if reraise:
                    raise
                
                if isinstance(e, BotError):
                    return {"error": e.user_message}
                else:
                    return {"error": user_message}
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_required(fields: list):
    """
    Декоратор для валидации обязательных полей
    
    Args:
        fields: Список обязательных полей
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Предполагаем что первый аргумент - это данные
            if args:
                data = args[0]
                for field in fields:
                    if field not in data or data[field] is None:
                        raise ValidationError(
                            field=field,
                            value=None,
                            message="Field is required"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Регистрируем стандартные обработчики
ErrorHandler.register(
    ConnectionError,
    lambda e, ctx: "Ошибка подключения к серверу. Проверьте интернет-соединение."
)

ErrorHandler.register(
    TimeoutError,
    lambda e, ctx: "Превышено время ожидания ответа. Попробуйте позже."
)

ErrorHandler.register(
    ValueError,
    lambda e, ctx: "Некорректные данные. Проверьте введенную информацию."
)


class ExceptionContext:
    """
    Контекстный менеджер для обработки исключений
    
    Использование:
    ```python
    async with ExceptionContext("user_id", 123) as ctx:
        # код который может выбросить исключение
        pass
    ```
    """
    
    def __init__(self, **context):
        self.context = context
        self.exception: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value:
            self.exception = exc_value
            ErrorHandler.handle(exc_value, self.context)
            return True  # Подавляем исключение
        return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        if exc_value:
            self.exception = exc_value
            ErrorHandler.handle(exc_value, self.context)
            return True  # Подавляем исключение
        return False