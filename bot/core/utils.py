"""
Утилиты и вспомогательные функции
"""

import re
import json
import hashlib
import logging
from typing import Optional, Dict, Any, List, Union, Callable, TypeVar, Tuple
from datetime import datetime, timedelta
from functools import wraps, lru_cache
import asyncio
from pathlib import Path


logger = logging.getLogger(__name__)

T = TypeVar('T')


class TextUtils:
    """Утилиты для работы с текстом"""
    
    @staticmethod
    def truncate(text: str, max_length: int = 4096, suffix: str = "...") -> str:
        """Обрезает текст до максимальной длины"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Экранирует специальные символы Markdown"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def extract_urls(text: str) -> List[str]:
        """Извлекает URL из текста"""
        url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(?:/(?:[-\w._~!$&\'()*+,;=:@]|%[\da-fA-F]{2})*)*(?:\?(?:[-\w._~!$&\'()*+,;=:@/?]|%[\da-fA-F]{2})*)?(?:#(?:[-\w._~!$&\'()*+,;=:@/?]|%[\da-fA-F]{2})*)?'
        return re.findall(url_pattern, text)
    
    @staticmethod
    def extract_hashtags(text: str) -> List[str]:
        """Извлекает хештеги из текста"""
        return re.findall(r'#\w+', text)
    
    @staticmethod
    def extract_mentions(text: str) -> List[str]:
        """Извлекает упоминания из текста"""
        return re.findall(r'@\w+', text)
    
    @staticmethod
    def clean_command(text: str) -> Tuple[str, str]:
        """Очищает команду и извлекает аргументы"""
        parts = text.strip().split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        # Убираем @ из команды
        if '@' in command:
            command = command.split('@')[0]
            
        return command, args


class CacheUtils:
    """Утилиты для кеширования"""
    
    @staticmethod
    def cache_key(*args, **kwargs) -> str:
        """Генерирует ключ кеша из аргументов"""
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    @staticmethod
    def ttl_cache(ttl_seconds: int = 300):
        """Декоратор для кеширования с TTL"""
        def decorator(func: Callable) -> Callable:
            cache = {}
            cache_times = {}
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = CacheUtils.cache_key(*args, **kwargs)
                now = datetime.now()
                
                # Проверяем кеш
                if key in cache and key in cache_times:
                    if now - cache_times[key] < timedelta(seconds=ttl_seconds):
                        return cache[key]
                
                # Вызываем функцию
                result = await func(*args, **kwargs)
                
                # Сохраняем в кеш
                cache[key] = result
                cache_times[key] = now
                
                return result
            
            return wrapper
        return decorator


class RateLimiter:
    """Ограничитель частоты запросов"""
    
    def __init__(self, max_calls: int, time_window: int):
        """
        Args:
            max_calls: Максимальное количество вызовов
            time_window: Временное окно в секундах
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = {}
    
    async def check_rate_limit(self, key: str) -> bool:
        """Проверяет, не превышен ли лимит"""
        now = datetime.now()
        
        # Очищаем старые записи
        self.calls = {
            k: v for k, v in self.calls.items()
            if now - v[-1] < timedelta(seconds=self.time_window)
        }
        
        # Проверяем лимит
        if key not in self.calls:
            self.calls[key] = []
        
        recent_calls = [
            call for call in self.calls[key]
            if now - call < timedelta(seconds=self.time_window)
        ]
        
        if len(recent_calls) >= self.max_calls:
            return False
        
        self.calls[key] = recent_calls + [now]
        return True
    
    def rate_limit(self, get_key: Callable):
        """Декоратор для ограничения частоты"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key = get_key(*args, **kwargs)
                
                if not await self.check_rate_limit(key):
                    raise Exception(f"Rate limit exceeded for {key}")
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator


class RetryUtils:
    """Утилиты для повторных попыток"""
    
    @staticmethod
    def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
        """Декоратор для повторных попыток"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                last_exception = None
                current_delay = delay
                
                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt < max_attempts - 1:
                            logger.warning(f"Попытка {attempt + 1}/{max_attempts} не удалась: {e}")
                            await asyncio.sleep(current_delay)
                            current_delay *= backoff
                        else:
                            logger.error(f"Все {max_attempts} попыток исчерпаны")
                
                raise last_exception
            
            return wrapper
        return decorator


class FileUtils:
    """Утилиты для работы с файлами"""
    
    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """Создает директорию если не существует"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @staticmethod
    def safe_json_load(file_path: Union[str, Path], default: Any = None) -> Any:
        """Безопасная загрузка JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка загрузки JSON из {file_path}: {e}")
            return default
    
    @staticmethod
    def safe_json_save(data: Any, file_path: Union[str, Path]) -> bool:
        """Безопасное сохранение JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения JSON в {file_path}: {e}")
            return False


class ValidationUtils:
    """Утилиты для валидации"""
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Проверяет валидность URL"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Проверяет валидность email"""
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        return email_pattern.match(email) is not None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Очищает имя файла от недопустимых символов"""
        # Заменяем недопустимые символы на подчеркивание
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Убираем точки в начале и конце
        filename = filename.strip('.')
        
        # Ограничиваем длину
        max_length = 255
        if len(filename) > max_length:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:max_length - len(ext) - 1] + '.' + ext if ext else name[:max_length]
        
        return filename


class AsyncUtils:
    """Утилиты для асинхронного программирования"""
    
    @staticmethod
    async def gather_with_timeout(
        *coroutines,
        timeout: float = 30.0,
        return_exceptions: bool = True
    ) -> List[Any]:
        """Выполняет корутины параллельно с таймаутом"""
        try:
            return await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=return_exceptions),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при выполнении {len(coroutines)} задач")
            return [None] * len(coroutines)
    
    @staticmethod
    def run_in_background(coro: Callable, *args, **kwargs):
        """Запускает корутину в фоне"""
        loop = asyncio.get_event_loop()
        task = loop.create_task(coro(*args, **kwargs))
        
        def done_callback(future):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Ошибка в фоновой задаче: {e}")
        
        task.add_done_callback(done_callback)
        return task


# Константы
MAX_MESSAGE_LENGTH = 4096
MAX_CAPTION_LENGTH = 1024
MAX_CALLBACK_DATA_LENGTH = 64

# Регулярные выражения
URL_REGEX = re.compile(r'https?://[^\s]+')
YOUTUBE_URL_REGEX = re.compile(r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)')
COMMAND_REGEX = re.compile(r'^/(\w+)(?:@\w+)?(?:\s+(.*))?$')