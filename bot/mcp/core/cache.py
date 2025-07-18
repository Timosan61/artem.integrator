"""
Кеширование для MCP
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MCPCache:
    """
    Кеш для результатов MCP функций
    
    Особенности:
    - TTL для каждой записи
    - Автоматическая очистка устаревших записей
    - Статистика использования
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Инициализация кеша
        
        Args:
            max_size: Максимальный размер кеша
        """
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.max_size = max_size
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_requests": 0
        }
        
    def get_key(self, server: str, function: str, parameters: Dict[str, Any]) -> str:
        """
        Генерирует ключ для кеша
        
        Args:
            server: Имя сервера
            function: Имя функции
            parameters: Параметры функции
            
        Returns:
            str: Ключ кеша
        """
        # Создаем стабильный ключ из параметров
        param_str = json.dumps(parameters, sort_keys=True)
        key_str = f"{server}:{function}:{param_str}"
        
        # Хешируем для компактности
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """
        Получает значение из кеша
        
        Args:
            key: Ключ кеша
            
        Returns:
            Optional[Any]: Значение или None
        """
        self.stats["total_requests"] += 1
        
        if key in self.cache:
            value, expires_at = self.cache[key]
            
            # Проверяем срок действия
            if datetime.now() < expires_at:
                self.stats["hits"] += 1
                logger.debug(f"📦 Cache hit: {key}")
                return value
            else:
                # Удаляем устаревшую запись
                del self.cache[key]
                logger.debug(f"🗑️ Cache expired: {key}")
        
        self.stats["misses"] += 1
        return None
    
    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Сохраняет значение в кеше
        
        Args:
            key: Ключ кеша
            value: Значение
            ttl: Время жизни в секундах
        """
        # Проверяем размер кеша
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        expires_at = datetime.now() + timedelta(seconds=ttl)
        self.cache[key] = (value, expires_at)
        logger.debug(f"💾 Cache set: {key}, TTL: {ttl}s")
    
    def delete(self, key: str) -> bool:
        """
        Удаляет значение из кеша
        
        Args:
            key: Ключ кеша
            
        Returns:
            bool: Было ли удалено значение
        """
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"🗑️ Cache delete: {key}")
            return True
        return False
    
    def clear(self):
        """Очищает весь кеш"""
        self.cache.clear()
        logger.info("🗑️ Cache cleared")
    
    def _evict_oldest(self):
        """Удаляет самую старую запись"""
        if not self.cache:
            return
        
        # Находим запись с самым ранним сроком истечения
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]
        self.stats["evictions"] += 1
        logger.debug(f"🗑️ Cache eviction: {oldest_key}")
    
    def cleanup_expired(self):
        """Удаляет все устаревшие записи"""
        now = datetime.now()
        expired_keys = [
            key for key, (_, expires_at) in self.cache.items()
            if expires_at <= now
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"🗑️ Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получает статистику кеша"""
        total_requests = self.stats["total_requests"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "evictions": self.stats["evictions"],
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "usage_percent": len(self.cache) / self.max_size * 100
        }