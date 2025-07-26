"""
Утилиты для структурированного логирования с контекстом

Предоставляет средства для создания логов с богатым контекстом,
включая trace_id, metadata и structured logging.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, Union
from datetime import datetime
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from enum import Enum

# Контекстные переменные для трассировки
trace_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
user_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
session_context: ContextVar[Optional[str]] = ContextVar('session_id', default=None)


class LogLevel(str, Enum):
    """Уровни логирования"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ComponentType(str, Enum):
    """Типы компонентов системы"""
    AGENT = "agent"
    SERVICE = "service"
    HANDLER = "handler"
    ADAPTER = "adapter"
    WEBHOOK = "webhook"
    MCP = "mcp"
    SDK = "sdk"
    API = "api"


@dataclass
class LogContext:
    """Контекст для структурированного логирования"""
    trace_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    component: Optional[ComponentType] = None
    operation: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class StructuredLogger:
    """
    Класс для структурированного логирования с контекстом
    
    Обеспечивает единообразное логирование с trace_id, метаданными
    и структурированным форматом для всех компонентов системы.
    """
    
    def __init__(self, name: str, component: ComponentType = ComponentType.SERVICE):
        """
        Инициализация структурированного логгера
        
        Args:
            name: Имя логгера
            component: Тип компонента
        """
        self.logger = logging.getLogger(name)
        self.component = component
    
    def _create_context(
        self, 
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogContext:
        """Создает контекст логирования"""
        return LogContext(
            trace_id=trace_id or trace_context.get() or self._generate_trace_id(),
            user_id=user_id or user_context.get(),
            session_id=session_id or session_context.get(),
            component=self.component,
            operation=operation,
            metadata=metadata or {}
        )
    
    def _generate_trace_id(self) -> str:
        """Генерирует новый trace_id"""
        return str(uuid.uuid4())[:8]
    
    def _format_message(
        self, 
        message: str, 
        context: LogContext,
        level: LogLevel,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Форматирует сообщение с контекстом
        
        Args:
            message: Основное сообщение
            context: Контекст логирования
            level: Уровень логирования
            extra_data: Дополнительные данные
            
        Returns:
            Отформатированное сообщение
        """
        # Базовая структура лога
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "trace_id": context.trace_id,
            "component": context.component.value,
            "message": message
        }
        
        # Добавляем опциональные поля
        if context.user_id:
            log_entry["user_id"] = context.user_id
        if context.session_id:
            log_entry["session_id"] = context.session_id
        if context.operation:
            log_entry["operation"] = context.operation
        if context.metadata:
            log_entry["metadata"] = context.metadata
        if extra_data:
            log_entry["extra"] = extra_data
        
        # Форматируем для читаемости
        if self.logger.level <= logging.DEBUG:
            # В DEBUG режиме возвращаем JSON для парсинга
            return json.dumps(log_entry, ensure_ascii=False, indent=2)
        else:
            # В обычном режиме возвращаем читаемый формат
            prefix = f"[TRACE:{context.trace_id}]"
            if context.user_id:
                prefix += f" [USER:{context.user_id}]"
            if context.operation:
                prefix += f" [{context.operation}]"
            return f"{prefix} {message}"
    
    def debug(
        self, 
        message: str, 
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Логирование уровня DEBUG"""
        context = self._create_context(trace_id, operation=operation, metadata=metadata)
        formatted_msg = self._format_message(message, context, LogLevel.DEBUG, kwargs)
        self.logger.debug(formatted_msg)
    
    def info(
        self, 
        message: str, 
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Логирование уровня INFO"""
        context = self._create_context(trace_id, operation=operation, metadata=metadata)
        formatted_msg = self._format_message(message, context, LogLevel.INFO, kwargs)
        self.logger.info(formatted_msg)
    
    def warning(
        self, 
        message: str, 
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """Логирование уровня WARNING"""
        context = self._create_context(trace_id, operation=operation, metadata=metadata)
        formatted_msg = self._format_message(message, context, LogLevel.WARNING, kwargs)
        self.logger.warning(formatted_msg)
    
    def error(
        self, 
        message: str, 
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Логирование уровня ERROR"""
        context = self._create_context(trace_id, operation=operation, metadata=metadata)
        formatted_msg = self._format_message(message, context, LogLevel.ERROR, kwargs)
        self.logger.error(formatted_msg, exc_info=exc_info)
    
    def critical(
        self, 
        message: str, 
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
        **kwargs
    ):
        """Логирование уровня CRITICAL"""
        context = self._create_context(trace_id, operation=operation, metadata=metadata)
        formatted_msg = self._format_message(message, context, LogLevel.CRITICAL, kwargs)
        self.logger.critical(formatted_msg, exc_info=exc_info)


class TraceContext:
    """
    Контекстный менеджер для трассировки операций
    
    Автоматически устанавливает и очищает контекстные переменные
    для трассировки запросов через всю систему.
    """
    
    def __init__(
        self, 
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        operation: Optional[str] = None
    ):
        """
        Инициализация контекста трассировки
        
        Args:
            trace_id: ID трассировки (генерируется автоматически если не указан)
            user_id: ID пользователя
            session_id: ID сессии
            operation: Название операции
        """
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.user_id = user_id
        self.session_id = session_id
        self.operation = operation
        
        # Сохраняем предыдущие значения для восстановления
        self._prev_trace = None
        self._prev_user = None
        self._prev_session = None
    
    def __enter__(self):
        """Вход в контекст"""
        self._prev_trace = trace_context.get()
        self._prev_user = user_context.get()
        self._prev_session = session_context.get()
        
        trace_context.set(self.trace_id)
        if self.user_id:
            user_context.set(self.user_id)
        if self.session_id:
            session_context.set(self.session_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекста"""
        trace_context.set(self._prev_trace)
        user_context.set(self._prev_user)
        session_context.set(self._prev_session)


def get_structured_logger(name: str, component: ComponentType = ComponentType.SERVICE) -> StructuredLogger:
    """
    Фабрика для создания структурированных логгеров
    
    Args:
        name: Имя логгера
        component: Тип компонента
        
    Returns:
        Настроенный StructuredLogger
    """
    return StructuredLogger(name, component)


def log_operation_start(
    logger: StructuredLogger, 
    operation: str, 
    trace_id: Optional[str] = None,
    **metadata
):
    """
    Логирует начало операции
    
    Args:
        logger: Структурированный логгер
        operation: Название операции
        trace_id: ID трассировки
        **metadata: Дополнительные метаданные
    """
    logger.info(
        f"🚀 Начало операции: {operation}",
        trace_id=trace_id,
        operation=operation,
        metadata={"status": "started", **metadata}
    )


def log_operation_success(
    logger: StructuredLogger, 
    operation: str, 
    trace_id: Optional[str] = None,
    duration: Optional[float] = None,
    **metadata
):
    """
    Логирует успешное завершение операции
    
    Args:
        logger: Структурированный логгер
        operation: Название операции
        trace_id: ID трассировки
        duration: Длительность операции в секундах
        **metadata: Дополнительные метаданные
    """
    meta = {"status": "success", **metadata}
    if duration is not None:
        meta["duration_seconds"] = duration
        
    logger.info(
        f"✅ Операция завершена успешно: {operation}",
        trace_id=trace_id,
        operation=operation,
        metadata=meta
    )


def log_operation_error(
    logger: StructuredLogger, 
    operation: str, 
    error: Union[str, Exception],
    trace_id: Optional[str] = None,
    duration: Optional[float] = None,
    **metadata
):
    """
    Логирует ошибку операции
    
    Args:
        logger: Структурированный логгер
        operation: Название операции
        error: Ошибка (строка или исключение)
        trace_id: ID трассировки
        duration: Длительность операции в секундах
        **metadata: Дополнительные метаданные
    """
    error_str = str(error)
    meta = {"status": "error", "error": error_str, **metadata}
    if duration is not None:
        meta["duration_seconds"] = duration
        
    logger.error(
        f"❌ Ошибка операции: {operation} - {error_str}",
        trace_id=trace_id,
        operation=operation,
        metadata=meta,
        exc_info=isinstance(error, Exception)
    )


# Готовые логгеры для основных компонентов
agent_logger = get_structured_logger("artem.agent", ComponentType.AGENT)
service_logger = get_structured_logger("artem.service", ComponentType.SERVICE)
handler_logger = get_structured_logger("artem.handler", ComponentType.HANDLER)
webhook_logger = get_structured_logger("artem.webhook", ComponentType.WEBHOOK)
mcp_logger = get_structured_logger("artem.mcp", ComponentType.MCP)
sdk_logger = get_structured_logger("artem.sdk", ComponentType.SDK)