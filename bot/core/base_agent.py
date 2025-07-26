"""
Базовый интерфейс для всех агентов

Определяет контракт, который должны реализовывать все агенты
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from .interfaces import Message, Response


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
        
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через цепочку агентов"""
        import logging
        import uuid
        
        logger = logging.getLogger(__name__)
        trace_id = str(uuid.uuid4())[:8]
        
        logger.info(f"🔗 [TRACE:{trace_id}] ChainedAgent начинает маршрутизацию сообщения")
        logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {message.user.id} (role: {message.user.role.value})")
        logger.info(f"📝 [TRACE:{trace_id}] Сообщение: '{message.text[:100]}{'...' if len(message.text) > 100 else ''}'")
        logger.info(f"🏗️ [TRACE:{trace_id}] Business сообщение: {getattr(message, 'is_business_message', False)}")
        logger.info(f"🔗 [TRACE:{trace_id}] Доступно агентов: {len(self.agents)}")
        
        # Показываем агентов в порядке приоритета
        for i, agent in enumerate(self.agents):
            logger.info(f"   {i+1}. {agent.get_name()} (приоритет: {agent.get_priority()})")
        
        # Проверяем каждого агента
        for i, agent in enumerate(self.agents):
            logger.info(f"🔍 [TRACE:{trace_id}] Проверяем агента {i+1}: {agent.get_name()}")
            
            try:
                can_handle = await agent.can_handle(message)
                logger.info(f"🎯 [TRACE:{trace_id}] {agent.get_name()} can_handle = {can_handle}")
                
                if can_handle:
                    logger.info(f"✅ [TRACE:{trace_id}] Агент {agent.get_name()} принял сообщение к обработке")
                    logger.info(f"⚡ [TRACE:{trace_id}] Делегируем обработку агенту {agent.get_name()}...")
                    
                    # Передаем trace_id агенту если он его поддерживает
                    response = await agent.process_message(message)
                    
                    # Добавляем информацию о том, какой агент обработал
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata["agent"] = agent.get_name()
                    response.metadata["trace_id"] = trace_id
                    
                    logger.info(f"✅ [TRACE:{trace_id}] Сообщение успешно обработано агентом {agent.get_name()}")
                    logger.info(f"📊 [TRACE:{trace_id}] Результат: {len(response.text)} символов")
                    
                    return response
                    
            except Exception as e:
                logger.error(f"❌ [TRACE:{trace_id}] Ошибка проверки агента {agent.get_name()}: {e}", exc_info=True)
                continue
                
        # Если никто не может обработать - возвращаем стандартный ответ
        logger.warning(f"⚠️ [TRACE:{trace_id}] Ни один агент не смог обработать сообщение")
        logger.warning(f"🚨 [TRACE:{trace_id}] Возвращаем стандартную ошибку")
        
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