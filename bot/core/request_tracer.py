"""
Система трассировки запросов через всю архитектуру бота

Обеспечивает сквозную трассировку запросов от webhook до ответа пользователю,
включая все промежуточные компоненты (агенты, сервисы, инструменты).
"""

import time
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from contextlib import asynccontextmanager

try:
    from .logging_utils import (
        get_structured_logger, ComponentType, TraceContext,
        log_operation_start, log_operation_success, log_operation_error
    )
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False


class TraceStatus(str, Enum):
    """Статусы трассировки запроса"""
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ComponentStep(str, Enum):
    """Этапы обработки в компонентах"""
    WEBHOOK_RECEIVED = "webhook_received"
    MESSAGE_PARSED = "message_parsed"
    AGENT_ROUTING = "agent_routing"
    AGENT_PROCESSING = "agent_processing"
    TOOL_EXECUTION = "tool_execution"
    RESPONSE_GENERATION = "response_generation"
    RESPONSE_SENT = "response_sent"
    ERROR_HANDLING = "error_handling"


@dataclass
class TraceEvent:
    """Событие в трассировке запроса"""
    timestamp: datetime
    component: ComponentType
    step: ComponentStep
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class RequestTrace:
    """Полная трассировка запроса"""
    trace_id: str
    user_id: str
    session_id: Optional[str]
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.STARTED
    events: List[TraceEvent] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Общая длительность запроса в миллисекундах"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None
    
    @property
    def component_durations(self) -> Dict[str, float]:
        """Длительность по компонентам"""
        durations = {}
        for event in self.events:
            if event.duration_ms:
                component = event.component.value
                durations[component] = durations.get(component, 0) + event.duration_ms
        return durations


class RequestTracer:
    """
    Система трассировки запросов
    
    Отслеживает жизненный цикл запросов от webhook до ответа,
    собирает метрики производительности и обеспечивает диагностику.
    """
    
    def __init__(self, max_traces: int = 1000, trace_ttl_hours: int = 24):
        """
        Инициализация трассировщика
        
        Args:
            max_traces: Максимальное количество хранимых трассировок
            trace_ttl_hours: Время жизни трассировки в часах
        """
        self.max_traces = max_traces
        self.trace_ttl = timedelta(hours=trace_ttl_hours)
        self.active_traces: Dict[str, RequestTrace] = {}
        self.completed_traces: Dict[str, RequestTrace] = {}
        
        # Метрики
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        # Логирование
        if STRUCTURED_LOGGING:
            self.logger = get_structured_logger("request_tracer", ComponentType.SERVICE)
        else:
            import logging
            self.logger = None
            self.fallback_logger = logging.getLogger(__name__)
    
    def create_trace(
        self, 
        user_id: str, 
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Создает новую трассировку запроса
        
        Args:
            user_id: ID пользователя
            session_id: ID сессии (опционально)
            metadata: Дополнительные метаданные
            
        Returns:
            trace_id: Уникальный ID трассировки
        """
        trace_id = str(uuid.uuid4())[:8]
        
        trace = RequestTrace(
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            start_time=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        self.active_traces[trace_id] = trace
        self.total_requests += 1
        
        # Очистка старых трассировок
        self._cleanup_old_traces()
        
        if self.logger:
            self.logger.info(
                f"🚀 Создана новая трассировка запроса",
                trace_id=trace_id,
                operation="trace_created",
                metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "total_active_traces": len(self.active_traces)
                }
            )
        else:
            self.fallback_logger.info(f"🚀 [TRACE:{trace_id}] Создана новая трассировка для пользователя {user_id}")
        
        return trace_id
    
    def add_event(
        self,
        trace_id: str,
        component: ComponentType,
        step: ComponentStep,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Добавляет событие в трассировку
        
        Args:
            trace_id: ID трассировки
            component: Компонент системы
            step: Этап обработки
            details: Детали события
            duration_ms: Длительность операции в миллисекундах
            success: Успешность операции
            error: Описание ошибки (если есть)
        """
        if trace_id not in self.active_traces:
            return  # Трассировка не найдена или уже завершена
        
        event = TraceEvent(
            timestamp=datetime.utcnow(),
            component=component,
            step=step,
            details=details or {},
            duration_ms=duration_ms,
            success=success,
            error=error
        )
        
        self.active_traces[trace_id].events.append(event)
        
        if self.logger:
            self.logger.info(
                f"📝 Событие трассировки: {step.value}",
                trace_id=trace_id,
                operation="trace_event",
                metadata={
                    "component": component.value,
                    "step": step.value,
                    "success": success,
                    "duration_ms": duration_ms,
                    "error": error,
                    "details": details or {}
                }
            )
        else:
            status_icon = "✅" if success else "❌"
            self.fallback_logger.info(
                f"{status_icon} [TRACE:{trace_id}] {component.value} -> {step.value}"
                + (f" ({duration_ms:.1f}ms)" if duration_ms else "")
                + (f" ERROR: {error}" if error else "")
            )
    
    def complete_trace(
        self, 
        trace_id: str, 
        status: TraceStatus = TraceStatus.COMPLETED,
        final_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Завершает трассировку запроса
        
        Args:
            trace_id: ID трассировки
            status: Финальный статус
            final_metadata: Финальные метаданные
        """
        if trace_id not in self.active_traces:
            return
        
        trace = self.active_traces[trace_id]
        trace.end_time = datetime.utcnow()
        trace.status = status
        
        if final_metadata:
            trace.metadata.update(final_metadata)
        
        # Обновляем статистику
        if status == TraceStatus.COMPLETED:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Перемещаем в завершенные
        self.completed_traces[trace_id] = trace
        del self.active_traces[trace_id]
        
        if self.logger:
            self.logger.info(
                f"🏁 Трассировка завершена",
                trace_id=trace_id,
                operation="trace_completed",
                metadata={
                    "status": status.value,
                    "duration_ms": trace.duration_ms,
                    "events_count": len(trace.events),
                    "user_id": trace.user_id,
                    "component_durations": trace.component_durations
                }
            )
        else:
            duration_str = f" за {trace.duration_ms:.1f}ms" if trace.duration_ms else ""
            self.fallback_logger.info(
                f"🏁 [TRACE:{trace_id}] Трассировка завершена: {status.value}{duration_str}"
            )
    
    def get_trace(self, trace_id: str) -> Optional[RequestTrace]:
        """Получает трассировку по ID"""
        return (self.active_traces.get(trace_id) or 
                self.completed_traces.get(trace_id))
    
    def get_active_traces(self) -> List[RequestTrace]:
        """Получает все активные трассировки"""
        return list(self.active_traces.values())
    
    def get_user_traces(self, user_id: str, limit: int = 10) -> List[RequestTrace]:
        """Получает трассировки пользователя"""
        user_traces = []
        
        # Активные трассировки
        for trace in self.active_traces.values():
            if trace.user_id == user_id:
                user_traces.append(trace)
        
        # Завершенные трассировки
        for trace in self.completed_traces.values():
            if trace.user_id == user_id:
                user_traces.append(trace)
        
        # Сортировка по времени создания (новые первыми)
        user_traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return user_traces[:limit]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Получает метрики производительности"""
        active_count = len(self.active_traces)
        completed_count = len(self.completed_traces)
        
        # Средняя длительность завершенных запросов
        completed_traces = list(self.completed_traces.values())
        avg_duration = 0
        if completed_traces:
            durations = [t.duration_ms for t in completed_traces if t.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Метрики по компонентам
        component_stats = {}
        for trace in completed_traces:
            for component, duration in trace.component_durations.items():
                if component not in component_stats:
                    component_stats[component] = {"total_ms": 0, "count": 0}
                component_stats[component]["total_ms"] += duration
                component_stats[component]["count"] += 1
        
        # Средняя длительность по компонентам
        for component, stats in component_stats.items():
            stats["avg_ms"] = stats["total_ms"] / stats["count"]
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / self.total_requests if self.total_requests > 0 else 0,
            "active_traces": active_count,
            "completed_traces": completed_count,
            "avg_duration_ms": avg_duration,
            "component_performance": component_stats
        }
    
    def _cleanup_old_traces(self):
        """Очищает старые трассировки"""
        now = datetime.utcnow()
        
        # Очистка завершенных трассировок старше TTL
        to_remove = []
        for trace_id, trace in self.completed_traces.items():
            if trace.end_time and (now - trace.end_time) > self.trace_ttl:
                to_remove.append(trace_id)
        
        for trace_id in to_remove:
            del self.completed_traces[trace_id]
        
        # Ограничение количества завершенных трассировок
        if len(self.completed_traces) > self.max_traces:
            # Оставляем только самые новые
            sorted_traces = sorted(
                self.completed_traces.items(),
                key=lambda x: x[1].end_time or x[1].start_time,
                reverse=True
            )
            
            self.completed_traces = dict(sorted_traces[:self.max_traces])
    
    @asynccontextmanager
    async def trace_operation(
        self,
        trace_id: str,
        component: ComponentType,
        step: ComponentStep,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Контекстный менеджер для трассировки операций
        
        Автоматически измеряет время выполнения и логирует результат
        """
        start_time = time.time()
        
        try:
            yield
            # Успешное выполнение
            duration_ms = (time.time() - start_time) * 1000
            self.add_event(
                trace_id, component, step, details, duration_ms, True
            )
        except Exception as e:
            # Ошибка выполнения
            duration_ms = (time.time() - start_time) * 1000
            self.add_event(
                trace_id, component, step, details, duration_ms, False, str(e)
            )
            raise


# Глобальный экземпляр трассировщика
request_tracer = RequestTracer()