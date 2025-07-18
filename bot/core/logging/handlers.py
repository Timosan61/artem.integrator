"""
Специальные обработчики логов
"""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
import json

from ..config import config
from .formatters import TelegramFormatter


class ErrorHandler(logging.Handler):
    """
    Обработчик для критических ошибок
    
    Особенности:
    - Отправка уведомлений администраторам
    - Группировка похожих ошибок
    - Rate limiting
    """
    
    def __init__(self):
        super().__init__()
        self.formatter = TelegramFormatter()
        self.error_counts = defaultdict(int)
        self.last_sent = defaultdict(datetime.now)
        self.rate_limit = timedelta(minutes=5)  # Не чаще раза в 5 минут
        
    def emit(self, record: logging.LogRecord):
        """Обрабатывает запись лога"""
        try:
            # Создаем ключ для группировки ошибок
            error_key = self._get_error_key(record)
            
            # Проверяем rate limit
            now = datetime.now()
            if now - self.last_sent[error_key] < self.rate_limit:
                self.error_counts[error_key] += 1
                return
            
            # Форматируем сообщение
            msg = self.format(record)
            
            # Добавляем счетчик если были пропущенные ошибки
            if self.error_counts[error_key] > 0:
                msg += f"\n\n<i>Пропущено похожих ошибок: {self.error_counts[error_key]}</i>"
                self.error_counts[error_key] = 0
            
            # Отправляем администраторам
            asyncio.create_task(self._send_to_admins(msg))
            self.last_sent[error_key] = now
            
        except Exception:
            # Не даем ошибкам в обработчике ломать приложение
            self.handleError(record)
    
    def _get_error_key(self, record: logging.LogRecord) -> str:
        """Создает ключ для группировки ошибок"""
        parts = [
            record.name,
            record.funcName,
            str(record.lineno)
        ]
        
        if record.exc_info:
            parts.append(record.exc_info[0].__name__)
        
        return ":".join(parts)
    
    async def _send_to_admins(self, message: str):
        """Отправляет сообщение администраторам"""
        try:
            from ...telegram_bot import bot
            
            for admin_id in config.admin.user_ids:
                try:
                    bot.send_message(
                        admin_id, 
                        message, 
                        parse_mode='HTML',
                        disable_notification=False
                    )
                except Exception as e:
                    # Логируем ошибку отправки, но не поднимаем исключение
                    logging.getLogger(__name__).error(
                        f"Failed to send error notification to admin {admin_id}: {e}"
                    )
                    
        except ImportError:
            # Бот еще не инициализирован
            pass


class MetricsHandler(logging.Handler):
    """
    Обработчик для сбора метрик из логов
    """
    
    def __init__(self):
        super().__init__()
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "warnings": 0,
            "last_seen": None
        })
        
    def emit(self, record: logging.LogRecord):
        """Обрабатывает запись лога"""
        try:
            # Собираем метрики по модулям
            module_metrics = self.metrics[record.name]
            module_metrics["count"] += 1
            module_metrics["last_seen"] = datetime.now()
            
            if record.levelno >= logging.ERROR:
                module_metrics["errors"] += 1
            elif record.levelno >= logging.WARNING:
                module_metrics["warnings"] += 1
            
            # Собираем метрики по пользователям если есть
            if hasattr(record, 'user_id'):
                user_metrics = self.metrics[f"user:{record.user_id}"]
                user_metrics["count"] += 1
                user_metrics["last_seen"] = datetime.now()
                
        except Exception:
            self.handleError(record)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает собранные метрики"""
        return dict(self.metrics)


class RotatingJSONFileHandler(logging.handlers.RotatingFileHandler):
    """
    Ротирующий файловый обработчик с JSON форматом
    """
    
    def __init__(self, filename: str, maxBytes: int = 10485760, backupCount: int = 5):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding='utf-8')
        from .formatters import JSONFormatter
        self.setFormatter(JSONFormatter())


class StructuredLoggingAdapter(logging.LoggerAdapter):
    """
    Адаптер для структурированного логирования
    
    Позволяет добавлять контекст к логам:
    
    logger = StructuredLoggingAdapter(logger, {"request_id": "123"})
    logger.info("Processing request", extra={"user_id": 456})
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Обрабатывает сообщение и добавляет контекст"""
        # Объединяем extra данные
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        
        return msg, kwargs


class AsyncHandler(logging.Handler):
    """
    Асинхронный обработчик логов
    
    Полезен для операций которые могут блокировать (например, сетевые вызовы)
    """
    
    def __init__(self, handler: logging.Handler):
        super().__init__()
        self.handler = handler
        self.queue: asyncio.Queue = asyncio.Queue()
        self.task: Optional[asyncio.Task] = None
        
    def start(self):
        """Запускает асинхронную обработку"""
        if not self.task:
            self.task = asyncio.create_task(self._process_logs())
    
    def stop(self):
        """Останавливает асинхронную обработку"""
        if self.task:
            self.task.cancel()
            self.task = None
    
    def emit(self, record: logging.LogRecord):
        """Добавляет запись в очередь"""
        try:
            self.queue.put_nowait(record)
        except asyncio.QueueFull:
            # Если очередь полна, обрабатываем синхронно
            self.handler.emit(record)
    
    async def _process_logs(self):
        """Обрабатывает логи из очереди"""
        while True:
            try:
                record = await self.queue.get()
                self.handler.emit(record)
            except asyncio.CancelledError:
                break
            except Exception:
                # Не даем ошибкам ломать обработку
                pass