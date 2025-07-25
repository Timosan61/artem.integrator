"""
Унифицированный агент

Главный агент, который использует цепочку ответственности
для обработки сообщений разными специализированными агентами
"""

import logging
from typing import Optional, List

from .base_agent import ChainedAgent, IAgent
from .agent_adapters import (
    IntelligentAgentAdapter,
    DefaultAgentAdapter
)
from .interfaces import Message, Response

logger = logging.getLogger(__name__)


class UnifiedAgent:
    """
    Главный агент системы
    
    Использует паттерн Chain of Responsibility для делегирования
    обработки сообщений специализированным агентам
    """
    
    def __init__(self):
        """Инициализация с автоматической настройкой цепочки агентов"""
        self._setup_agent_chain()
        
    def _setup_agent_chain(self):
        """Настраивает цепочку агентов"""
        agents: List[IAgent] = []
        
        # Добавляем агентов в порядке приоритета
        try:
            # 1. Intelligent Agent только для владельца бота (приоритет 90)
            agents.append(IntelligentAgentAdapter())
            logger.info("✅ IntelligentAgent добавлен в цепочку")
        except Exception as e:
            logger.warning(f"⚠️ IntelligentAgent недоступен: {e}")
            
        try:
            # 2. Default Agent (ArtemAgent) для всех остальных + Business (приоритет 10)
            agents.append(DefaultAgentAdapter())
            logger.info("✅ DefaultAgent добавлен в цепочку")
        except Exception as e:
            logger.error(f"❌ DefaultAgent недоступен: {e}")
            
        # Создаем цепочку
        self.chain = ChainedAgent(agents)
        logger.info(f"🔗 Цепочка агентов создана с {len(agents)} агентами")
        
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает входящее сообщение
        
        Args:
            message: Сообщение для обработки
            
        Returns:
            Response с ответом от подходящего агента
        """
        logger.info(f"📨 UnifiedAgent обрабатывает сообщение от {message.user.id} (role: {message.user.role.value})")
        
        try:
            # Делегируем обработку цепочке
            response = await self.chain.process_message(message)
            
            # Логируем, какой агент обработал
            if "agent" in response.metadata:
                logger.info(f"✅ Сообщение обработано агентом: {response.metadata['agent']}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return Response(
                text="Извините, произошла ошибка при обработке вашего сообщения.",
                metadata={"error": str(e)}
            )
            
    async def clear_user_memory(self, user_id: int) -> bool:
        """
        Очищает память пользователя во всех агентах
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если успешно
        """
        logger.info(f"🧹 Очистка памяти пользователя {user_id}")
        return await self.chain.clear_user_memory(user_id)
        
    def get_status(self) -> dict:
        """
        Возвращает статус всех агентов
        
        Returns:
            Словарь со статусом системы
        """
        return self.chain.get_status()
        
    async def get_agent_for_message(self, message: Message) -> Optional[str]:
        """
        Определяет, какой агент будет обрабатывать сообщение
        
        Args:
            message: Сообщение для анализа
            
        Returns:
            Имя агента или None
        """
        for agent in self.chain.agents:
            if await agent.can_handle(message):
                return agent.get_name()
        return None


# Глобальный экземпляр унифицированного агента
unified_agent = UnifiedAgent()