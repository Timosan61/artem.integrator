"""
Декораторы для различных проверок и функциональности
"""

import logging
import time
import asyncio
from functools import wraps
from typing import Callable, Optional, Any, Dict, List

from .interfaces import User, UserRole, AuthorizationError, ServiceError
from .config import config


logger = logging.getLogger(__name__)


def require_admin(func: Callable) -> Callable:
    """Декоратор для проверки прав администратора"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Ищем объект User в аргументах
        user = None
        for arg in args:
            if isinstance(arg, User):
                user = arg
                break
        
        # Проверяем в kwargs
        if not user:
            user = kwargs.get('user')
        
        if not user:
            raise AuthorizationError("Пользователь не найден")
        
        if user.role != UserRole.ADMIN:
            raise AuthorizationError("Требуются права администратора")
        
        return await func(*args, **kwargs)
    
    return wrapper


def require_role(role: UserRole):
    """Декоратор для проверки роли пользователя"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Ищем объект User в аргументах
            user = None
            for arg in args:
                if isinstance(arg, User):
                    user = arg
                    break
            
            if not user:
                user = kwargs.get('user')
            
            if not user:
                raise AuthorizationError("Пользователь не найден")
            
            # Админ имеет доступ ко всему
            if user.role == UserRole.ADMIN:
                return await func(*args, **kwargs)
            
            if user.role != role:
                raise AuthorizationError(f"Требуется роль {role.value}")
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def log_execution(level: str = "INFO"):
    """Декоратор для логирования выполнения функции"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            logger.log(getattr(logging, level), f"Начало выполнения {func_name}")
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(getattr(logging, level), f"Успешное выполнение {func_name} за {elapsed:.2f}с")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Ошибка в {func_name} после {elapsed:.2f}с: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = func.__name__
            
            logger.log(getattr(logging, level), f"Начало выполнения {func_name}")
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                logger.log(getattr(logging, level), f"Успешное выполнение {func_name} за {elapsed:.2f}с")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"Ошибка в {func_name} после {elapsed:.2f}с: {e}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def measure_time(func: Callable) -> Callable:
    """Декоратор для измерения времени выполнения"""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} выполнено за {elapsed:.3f}с")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} завершилось с ошибкой за {elapsed:.3f}с")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} выполнено за {elapsed:.3f}с")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} завершилось с ошибкой за {elapsed:.3f}с")
            raise
    
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def handle_errors(default_return: Any = None, log_errors: bool = True):
    """Декоратор для обработки ошибок"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                return default_return
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
                return default_return
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_input(**validators):
    """Декоратор для валидации входных параметров"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Получаем имена параметров функции
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Валидируем каждый параметр
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Неверное значение параметра {param_name}: {value}")
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            for param_name, validator in validators.items():
                if param_name in bound_args.arguments:
                    value = bound_args.arguments[param_name]
                    if not validator(value):
                        raise ValueError(f"Неверное значение параметра {param_name}: {value}")
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def deprecated(reason: str):
    """Декоратор для пометки устаревших функций"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger.warning(f"{func.__name__} устарела: {reason}")
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger.warning(f"{func.__name__} устарела: {reason}")
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def singleton(cls):
    """Декоратор для создания синглтона"""
    instances = {}
    
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance


def async_timeout(seconds: float):
    """Декоратор для установки таймаута на асинхронную функцию"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"{func.__name__} превысила таймаут {seconds}с")
                raise
        
        return wrapper
    
    return decorator


def memoize(maxsize: int = 128):
    """Декоратор для мемоизации результатов функции"""
    def decorator(func: Callable) -> Callable:
        cache = {}
        cache_order = []
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Создаем ключ из аргументов
            key = str(args) + str(sorted(kwargs.items()))
            
            # Проверяем кеш
            if key in cache:
                return cache[key]
            
            # Вызываем функцию
            result = await func(*args, **kwargs)
            
            # Сохраняем в кеш
            cache[key] = result
            cache_order.append(key)
            
            # Очищаем старые записи если превышен размер
            if len(cache) > maxsize:
                oldest_key = cache_order.pop(0)
                del cache[oldest_key]
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            key = str(args) + str(sorted(kwargs.items()))
            
            if key in cache:
                return cache[key]
            
            result = func(*args, **kwargs)
            
            cache[key] = result
            cache_order.append(key)
            
            if len(cache) > maxsize:
                oldest_key = cache_order.pop(0)
                del cache[oldest_key]
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def ensure_service_enabled(service_name: str):
    """Декоратор для проверки, что сервис включен"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            service_status = {
                'openai': config.openai.enabled,
                'anthropic': config.anthropic.enabled,
                'zep': config.zep.enabled,
                'voice': config.voice.enabled,
                'social_media': config.social_media.enabled,
                'mcp': config.mcp.enabled
            }
            
            if not service_status.get(service_name, False):
                raise ServiceError(f"Сервис {service_name} отключен")
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator