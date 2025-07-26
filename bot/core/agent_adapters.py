"""
Адаптеры для существующих агентов

Приводит существующие агенты к единому интерфейсу IAgent
"""

import logging
from typing import Optional, Dict, Any

try:
    from .logging_utils import (
        get_structured_logger, ComponentType, TraceContext,
        log_operation_start, log_operation_success, log_operation_error
    )
    from .request_tracer import request_tracer, ComponentStep
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False

from .base_agent import IAgent
from .interfaces import Message, Response, UserRole

logger = logging.getLogger(__name__)

# Инициализируем структурированные логгеры если доступны
if STRUCTURED_LOGGING:
    adapter_logger = get_structured_logger("agent_adapter", ComponentType.ADAPTER)
else:
    adapter_logger = None


class UnifiedAgentAdapter(IAgent):
    """Адаптер для Unified Agent с Claude Code SDK"""
    
    def __init__(self):
        self._service = None
        self.structured_logger = adapter_logger if STRUCTURED_LOGGING else None
        self._init_service()
        
    def _init_service(self):
        """Ленивая инициализация сервиса"""
        try:
            from .unified_agent import unified_agent
            self._service = unified_agent
            logger.info("✅ UnifiedAgentAdapter инициализирован")
        except ImportError as e:
            logger.warning(f"⚠️ Unified Agent недоступен: {e}")
            
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через Unified Agent"""
        trace_id = getattr(message, 'trace_id', None)
        
        if not self._service:
            if self.structured_logger and trace_id:
                self.structured_logger.error(
                    "❌ Unified Agent недоступен",
                    trace_id=trace_id,
                    operation="service_unavailable",
                    metadata={"service_available": False}
                )
            return Response(text="Unified Agent недоступен", metadata={"error": "Service not available"})
        
        # Трассировка обработки сообщения через UnifiedAgent
        if STRUCTURED_LOGGING and trace_id:
            async with request_tracer.trace_operation(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                details={"agent": "UnifiedAgent", "user_id": message.user.id}
            ):
                return await self._service.process_message(message)
        else:
            return await self._service.process_message(message)
        
    async def can_handle(self, message: Message) -> bool:
        """Проверяет, может ли обработать сообщение"""
        import uuid
        trace_id = getattr(message, 'trace_id', str(uuid.uuid4())[:8])
        
        if self.structured_logger:
            self.structured_logger.info(
                "🔍 UnifiedAgentAdapter: анализ возможности обработки",
                trace_id=trace_id,
                operation="can_handle_analysis",
                metadata={
                    "user_id": message.user.id,
                    "user_role": message.user.role.value,
                    "is_business_message": getattr(message, 'is_business_message', False),
                    "message_length": len(message.text)
                }
            )
        else:
            logger.info(f"🔍 [TRACE:{trace_id}] UnifiedAgentAdapter: анализ возможности обработки")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {message.user.id}")
            logger.info(f"🏷️ [TRACE:{trace_id}] Роль пользователя: {message.user.role.value}")
            logger.info(f"🏗️ [TRACE:{trace_id}] Business сообщение: {getattr(message, 'is_business_message', False)}")
        
        # Unified Agent обрабатывает ВСЕ сообщения от администраторов бота
        from ..core.config import config
        
        # Если UnifiedAgent недоступен, не обрабатываем
        if not self._service:
            if self.structured_logger:
                self.structured_logger.warning(
                    "❌ UnifiedAgent недоступен или не инициализирован",
                    trace_id=trace_id,
                    operation="availability_check",
                    metadata={"service_available": False}
                )
            else:
                logger.warning(f"❌ [TRACE:{trace_id}] UnifiedAgent недоступен или не инициализирован")
            return False
            
        # Проверяем, что пользователь админ
        if message.user.role != UserRole.ADMIN:
            if self.structured_logger:
                self.structured_logger.info(
                    "❌ Отклонено: пользователь не администратор",
                    trace_id=trace_id,
                    operation="role_check",
                    metadata={"user_role": message.user.role.value, "required_role": "admin"}
                )
            else:
                logger.info(f"❌ [TRACE:{trace_id}] Отклонено: пользователь не администратор")
            return False
            
        # UnifiedAgent обрабатывает ВСЕ сообщения от любого администратора
        if self.structured_logger:
            self.structured_logger.info(
                "✅ Принято: администратор может использовать UnifiedAgent",
                trace_id=trace_id,
                operation="admin_access_granted",
                metadata={
                    "user_id": message.user.id,
                    "access_type": "full_admin_access",
                    "agent_priority": self.get_priority()
                }
            )
        else:
            logger.info(f"✅ [TRACE:{trace_id}] Принято: администратор может использовать UnifiedAgent")
            logger.debug(f"Admin user {message.user.id} can access UnifiedAgent for any message")
        
        # Администратор всегда направляется к UnifiedAgent
        return True
        
    def get_name(self) -> str:
        return "UnifiedAgent"
        
    def get_priority(self) -> int:
        return 90  # Высокий приоритет для админов
        
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        if self._service:
            return self._service.get_status()
        return {
            "name": self.get_name(),
            "enabled": False,
            "error": "Service not initialized"
        }



class DefaultAgentAdapter(IAgent):
    """Адаптер для стандартного AI агента"""
    
    def __init__(self):
        self._agent = None
        self.structured_logger = adapter_logger if STRUCTURED_LOGGING else None
        self._init_agent()
        
    def _init_agent(self):
        """Ленивая инициализация агента"""
        try:
            from .agent import AgentFactory
            self._agent = AgentFactory.get_agent()
            logger.info("✅ DefaultAgentAdapter инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации стандартного агента: {e}")
            
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через стандартный агент"""
        trace_id = getattr(message, 'trace_id', None)
        
        if not self._agent:
            if self.structured_logger and trace_id:
                self.structured_logger.error(
                    "❌ DefaultAgent не инициализирован",
                    trace_id=trace_id,
                    operation="agent_unavailable",
                    metadata={"agent_initialized": False}
                )
            return Response(
                text="Извините, сервис временно недоступен",
                metadata={"error": "Agent not initialized"}
            )
        
        # Трассировка обработки сообщения через DefaultAgent
        if STRUCTURED_LOGGING and trace_id:
            async with request_tracer.trace_operation(
                trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                details={"agent": "DefaultAgent", "user_id": message.user.id}
            ):
                return await self._agent.process_message(message)
        else:
            return await self._agent.process_message(message)
        
    async def can_handle(self, message: Message) -> bool:
        """Стандартный агент может обработать любое сообщение"""
        import uuid
        trace_id = getattr(message, 'trace_id', str(uuid.uuid4())[:8])
        
        if self.structured_logger:
            self.structured_logger.info(
                "🔍 DefaultAgentAdapter: анализ возможности обработки",
                trace_id=trace_id,
                operation="can_handle_analysis",
                metadata={
                    "user_id": message.user.id,
                    "user_role": message.user.role.value,
                    "is_business_message": getattr(message, 'is_business_message', False),
                    "agent_initialized": self._agent is not None,
                    "agent_priority": self.get_priority()
                }
            )
        else:
            logger.info(f"🔍 [TRACE:{trace_id}] DefaultAgentAdapter: анализ возможности обработки")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {message.user.id}")
            logger.info(f"🏷️ [TRACE:{trace_id}] Роль пользователя: {message.user.role.value}")
            logger.info(f"🏗️ [TRACE:{trace_id}] Business сообщение: {getattr(message, 'is_business_message', False)}")
        
        if self._agent is not None:
            if self.structured_logger:
                self.structured_logger.info(
                    "✅ Принято: DefaultAgent (ArtemAgent) готов обработать сообщение",
                    trace_id=trace_id,
                    operation="agent_ready",
                    metadata={"agent_type": "ArtemAgent", "fallback_role": True}
                )
            else:
                logger.info(f"✅ [TRACE:{trace_id}] Принято: DefaultAgent (ArtemAgent) готов обработать сообщение")
            return True
        else:
            if self.structured_logger:
                self.structured_logger.warning(
                    "❌ Отклонено: DefaultAgent не инициализирован",
                    trace_id=trace_id,
                    operation="agent_unavailable",
                    metadata={"error": "agent_not_initialized"}
                )
            else:
                logger.warning(f"❌ [TRACE:{trace_id}] Отклонено: DefaultAgent не инициализирован")
            return False
        
    def get_name(self) -> str:
        return "DefaultAgent"
        
    def get_priority(self) -> int:
        return 10  # Низкий приоритет - fallback агент
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память пользователя"""
        if self._agent:
            return await self._agent.clear_user_memory(user_id)
        return False