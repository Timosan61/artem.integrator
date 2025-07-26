"""
Базовый интерфейс для всех агентов

Определяет контракт, который должны реализовывать все агенты
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from .interfaces import Message, Response

try:
    from .logging_utils import (
        get_structured_logger, ComponentType, TraceContext,
        log_operation_start, log_operation_success, log_operation_error
    )
    from .request_tracer import request_tracer, ComponentStep
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False


class IAgent(ABC):
    """Базовый интерфейс для всех агентов"""
    
    @abstractmethod
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает входящее сообщение
        
        Args:
            message: Сообщение для обработки
            
        Returns:
            Response с ответом агента
        """
        pass
        
    @abstractmethod
    async def can_handle(self, message: Message) -> bool:
        """
        Проверяет, может ли агент обработать данное сообщение
        
        Args:
            message: Сообщение для проверки
            
        Returns:
            True если агент может обработать сообщение
        """
        pass
        
    @abstractmethod
    def get_name(self) -> str:
        """Возвращает имя агента"""
        pass
        
    @abstractmethod
    def get_priority(self) -> int:
        """
        Возвращает приоритет агента (больше = выше приоритет)
        
        Returns:
            Приоритет от 0 до 100
        """
        pass
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """
        Очищает память пользователя (опционально)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """
        Возвращает статус агента (опционально)
        
        Returns:
            Словарь со статусом
        """
        return {
            "name": self.get_name(),
            "priority": self.get_priority(),
            "enabled": True
        }


class ChainedAgent(IAgent):
    """
    Агент, использующий цепочку ответственности
    
    Передает сообщение по цепочке агентов, пока один из них не обработает
    """
    
    def __init__(self, agents: List[IAgent]):
        """
        Args:
            agents: Список агентов в порядке приоритета
        """
        self.agents = sorted(agents, key=lambda a: a.get_priority(), reverse=True)
        
        # Инициализируем структурированное логирование
        if STRUCTURED_LOGGING:
            self.structured_logger = get_structured_logger("chained_agent", ComponentType.AGENT)
        else:
            self.structured_logger = None
        
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через цепочку агентов"""
        import logging
        import uuid
        
        logger = logging.getLogger(__name__)
        
        # Получаем trace_id из сообщения или создаем новый
        trace_id = getattr(message, 'trace_id', str(uuid.uuid4())[:8])
        
        # Добавляем trace_id к сообщению если его не было
        if not hasattr(message, 'trace_id'):
            message.trace_id = trace_id
        
        # Структурированное логирование
        if self.structured_logger:
            self.structured_logger.info(
                "🔗 ChainedAgent начинает маршрутизацию сообщения",
                trace_id=trace_id,
                operation="agent_routing_start",
                metadata={
                    "user_id": message.user.id,
                    "user_role": message.user.role.value,
                    "is_business_message": getattr(message, 'is_business_message', False),
                    "message_length": len(message.text),
                    "available_agents": len(self.agents),
                    "agents_list": [agent.get_name() for agent in self.agents]
                }
            )
        else:
            logger.info(f"🔗 [TRACE:{trace_id}] ChainedAgent начинает маршрутизацию сообщения")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {message.user.id} (role: {message.user.role.value})")
            logger.info(f"📝 [TRACE:{trace_id}] Сообщение: '{message.text[:100]}{'...' if len(message.text) > 100 else ''}'")
            logger.info(f"🏗️ [TRACE:{trace_id}] Business сообщение: {getattr(message, 'is_business_message', False)}")
            logger.info(f"🔗 [TRACE:{trace_id}] Доступно агентов: {len(self.agents)}")
        
        # Добавляем событие трассировки
        if STRUCTURED_LOGGING:
            request_tracer.add_event(
                trace_id, 
                ComponentType.AGENT, 
                ComponentStep.AGENT_ROUTING,
                details={
                    "available_agents": len(self.agents),
                    "agent_names": [agent.get_name() for agent in self.agents]
                }
            )
        
        # Показываем агентов в порядке приоритета
        if self.structured_logger:
            agents_info = []
            for i, agent in enumerate(self.agents):
                agents_info.append({
                    "position": i + 1,
                    "name": agent.get_name(),
                    "priority": agent.get_priority()
                })
            self.structured_logger.info(
                "📋 Список агентов в порядке приоритета",
                trace_id=trace_id,
                operation="agents_list",
                metadata={"agents": agents_info}
            )
        else:
            for i, agent in enumerate(self.agents):
                logger.info(f"   {i+1}. {agent.get_name()} (приоритет: {agent.get_priority()})")
        
        # Проверяем каждого агента
        for i, agent in enumerate(self.agents):
            agent_name = agent.get_name()
            
            if self.structured_logger:
                self.structured_logger.info(
                    f"🔍 Проверяем агента {i+1}: {agent_name}",
                    trace_id=trace_id,
                    operation="agent_check",
                    metadata={"agent_name": agent_name, "position": i+1}
                )
            else:
                logger.info(f"🔍 [TRACE:{trace_id}] Проверяем агента {i+1}: {agent_name}")
            
            try:
                # Трассировка проверки агента
                if STRUCTURED_LOGGING:
                    async with request_tracer.trace_operation(
                        trace_id, ComponentType.AGENT, ComponentStep.AGENT_ROUTING,
                        details={"operation": "can_handle_check", "agent": agent_name}
                    ):
                        can_handle = await agent.can_handle(message)
                else:
                    can_handle = await agent.can_handle(message)
                
                if self.structured_logger:
                    self.structured_logger.info(
                        f"🎯 {agent_name} can_handle = {can_handle}",
                        trace_id=trace_id,
                        operation="can_handle_result",
                        metadata={"agent_name": agent_name, "can_handle": can_handle}
                    )
                else:
                    logger.info(f"🎯 [TRACE:{trace_id}] {agent_name} can_handle = {can_handle}")
                
                if can_handle:
                    if self.structured_logger:
                        self.structured_logger.info(
                            f"✅ Агент {agent_name} принял сообщение к обработке",
                            trace_id=trace_id,
                            operation="agent_selected",
                            metadata={"selected_agent": agent_name, "position": i+1}
                        )
                    else:
                        logger.info(f"✅ [TRACE:{trace_id}] Агент {agent_name} принял сообщение к обработке")
                        logger.info(f"⚡ [TRACE:{trace_id}] Делегируем обработку агенту {agent_name}...")
                    
                    # Трассировка обработки сообщения
                    if STRUCTURED_LOGGING:
                        async with request_tracer.trace_operation(
                            trace_id, ComponentType.AGENT, ComponentStep.AGENT_PROCESSING,
                            details={"agent": agent_name, "user_id": message.user.id}
                        ):
                            response = await agent.process_message(message)
                    else:
                        response = await agent.process_message(message)
                    
                    # Добавляем информацию о том, какой агент обработал
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata["agent"] = agent_name
                    response.metadata["trace_id"] = trace_id
                    
                    if self.structured_logger:
                        self.structured_logger.info(
                            f"✅ Сообщение успешно обработано агентом {agent_name}",
                            trace_id=trace_id,
                            operation="agent_processing_success",
                            metadata={
                                "agent_name": agent_name,
                                "response_length": len(response.text),
                                "has_metadata": bool(response.metadata)
                            }
                        )
                    else:
                        logger.info(f"✅ [TRACE:{trace_id}] Сообщение успешно обработано агентом {agent_name}")
                        logger.info(f"📊 [TRACE:{trace_id}] Результат: {len(response.text)} символов")
                    
                    return response
                    
            except Exception as e:
                if self.structured_logger:
                    self.structured_logger.error(
                        f"❌ Ошибка проверки агента {agent_name}: {str(e)}",
                        trace_id=trace_id,
                        operation="agent_check_error",
                        metadata={"agent_name": agent_name, "error": str(e)}
                    )
                else:
                    logger.error(f"❌ [TRACE:{trace_id}] Ошибка проверки агента {agent_name}: {e}", exc_info=True)
                
                # Добавляем событие ошибки в трассировку
                if STRUCTURED_LOGGING:
                    request_tracer.add_event(
                        trace_id, ComponentType.AGENT, ComponentStep.ERROR_HANDLING,
                        details={"agent": agent_name, "error": str(e)},
                        success=False, error=str(e)
                    )
                continue
                
        # Если никто не может обработать - возвращаем стандартный ответ
        if self.structured_logger:
            self.structured_logger.warning(
                "⚠️ Ни один агент не смог обработать сообщение",
                trace_id=trace_id,
                operation="no_agent_found",
                metadata={
                    "total_agents_checked": len(self.agents),
                    "user_id": message.user.id,
                    "message_length": len(message.text)
                }
            )
        else:
            logger.warning(f"⚠️ [TRACE:{trace_id}] Ни один агент не смог обработать сообщение")
            logger.warning(f"🚨 [TRACE:{trace_id}] Возвращаем стандартную ошибку")
        
        # Добавляем событие отсутствия подходящего агента
        if STRUCTURED_LOGGING:
            request_tracer.add_event(
                trace_id, ComponentType.AGENT, ComponentStep.ERROR_HANDLING,
                details={"reason": "no_suitable_agent_found", "agents_checked": len(self.agents)},
                success=False, error="No suitable agent found"
            )
        
        return Response(
            text="Извините, я не могу обработать ваш запрос.",
            metadata={"error": "No suitable agent found", "trace_id": trace_id}
        )
        
    async def can_handle(self, message: Message) -> bool:
        """Проверяет, может ли хотя бы один агент обработать сообщение"""
        for agent in self.agents:
            if await agent.can_handle(message):
                return True
        return False
        
    def get_name(self) -> str:
        return "ChainedAgent"
        
    def get_priority(self) -> int:
        return 50  # Средний приоритет
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память во всех агентах"""
        results = []
        for agent in self.agents:
            results.append(await agent.clear_user_memory(user_id))
        return all(results)
        
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус всех агентов в цепочке"""
        return {
            "name": self.get_name(),
            "agents": [agent.get_status() for agent in self.agents],
            "total_agents": len(self.agents)
        }