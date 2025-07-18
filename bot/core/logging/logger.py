"""
Основной модуль логирования
"""

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

from ..config import config
from .formatters import ColoredFormatter, JSONFormatter
from .handlers import ErrorHandler, MetricsHandler


class BotLogger:
    """
    Централизованный логгер для бота
    
    Особенности:
    - Разные уровни логирования для разных модулей
    - Ротация логов
    - Цветной вывод в консоль
    - JSON логи для production
    - Отправка критических ошибок администратору
    """
    
    _instance = None
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logs_dir = config.logs_dir
        self.logs_dir.mkdir(exist_ok=True)
        
        # Настройка корневого логгера
        self._setup_root_logger()
        
        # Настройка специфичных логгеров
        self._setup_module_loggers()
    
    def _setup_root_logger(self):
        """Настройка корневого логгера"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        
        # Очищаем существующие обработчики
        root_logger.handlers.clear()
        
        # Консольный вывод
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if config.debug else logging.INFO)
        
        if config.environment.value == "development":
            console_handler.setFormatter(ColoredFormatter())
        else:
            console_handler.setFormatter(JSONFormatter())
        
        root_logger.addHandler(console_handler)
        
        # Файловый вывод
        self._add_file_handlers(root_logger)
        
        # Обработчик ошибок
        if config.environment.value == "production":
            error_handler = ErrorHandler()
            error_handler.setLevel(logging.ERROR)
            root_logger.addHandler(error_handler)
    
    def _add_file_handlers(self, logger: logging.Logger):
        """Добавляет файловые обработчики"""
        # Общий лог
        general_log = self.logs_dir / "bot.log"
        general_handler = logging.handlers.RotatingFileHandler(
            general_log,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        general_handler.setFormatter(JSONFormatter())
        general_handler.setLevel(logging.INFO)
        logger.addHandler(general_handler)
        
        # Лог ошибок
        error_log = self.logs_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        error_handler.setFormatter(JSONFormatter())
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)
        
        # Debug лог (только в development)
        if config.debug:
            debug_log = self.logs_dir / "debug.log"
            debug_handler = logging.handlers.RotatingFileHandler(
                debug_log,
                maxBytes=20 * 1024 * 1024,  # 20MB
                backupCount=2,
                encoding='utf-8'
            )
            debug_handler.setFormatter(JSONFormatter())
            debug_handler.setLevel(logging.DEBUG)
            logger.addHandler(debug_handler)
    
    def _setup_module_loggers(self):
        """Настройка логгеров для модулей"""
        # Настройки уровней для разных модулей
        module_levels = {
            "bot.webhook": logging.INFO,
            "bot.core": logging.INFO,
            "bot.mcp": logging.DEBUG if config.mcp.enabled else logging.INFO,
            "bot.services": logging.INFO,
            "httpx": logging.WARNING,
            "telebot": logging.WARNING,
            "uvicorn": logging.INFO,
            "openai": logging.WARNING,
            "anthropic": logging.WARNING
        }
        
        for module_name, level in module_levels.items():
            logger = logging.getLogger(module_name)
            logger.setLevel(level)
            self._loggers[module_name] = logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Получает логгер для модуля
        
        Args:
            name: Имя модуля
            
        Returns:
            logging.Logger: Настроенный логгер
        """
        if name in self._loggers:
            return self._loggers[name]
        
        logger = logging.getLogger(name)
        self._loggers[name] = logger
        return logger
    
    def add_metrics_handler(self, metrics_handler: MetricsHandler):
        """Добавляет обработчик метрик"""
        root_logger = logging.getLogger()
        root_logger.addHandler(metrics_handler)
    
    def log_startup(self):
        """Логирует запуск бота"""
        logger = self.get_logger("bot.startup")
        logger.info("=" * 50)
        logger.info("🤖 Artyom Integrator Bot Starting...")
        logger.info(f"📅 Time: {datetime.now().isoformat()}")
        logger.info(f"🌍 Environment: {config.environment.value}")
        logger.info(f"🐛 Debug: {config.debug}")
        logger.info(f"📁 Logs: {self.logs_dir}")
        
        # Статус сервисов
        status = config.get_status_info()
        logger.info(f"📊 Services: {json.dumps(status['services'], indent=2)}")
        logger.info("=" * 50)
    
    def log_shutdown(self):
        """Логирует завершение работы бота"""
        logger = self.get_logger("bot.shutdown")
        logger.info("=" * 50)
        logger.info("🛑 Artyom Integrator Bot Shutting down...")
        logger.info(f"📅 Time: {datetime.now().isoformat()}")
        logger.info("=" * 50)


# Глобальный экземпляр
_bot_logger = BotLogger()


def get_logger(name: str) -> logging.Logger:
    """
    Получает логгер для модуля
    
    Args:
        name: Имя модуля (обычно __name__)
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    return _bot_logger.get_logger(name)


def setup_logging():
    """Инициализирует систему логирования"""
    _bot_logger.log_startup()


def shutdown_logging():
    """Завершает работу системы логирования"""
    _bot_logger.log_shutdown()