"""
Адаптеры для существующих агентов

Приводит существующие агенты к единому интерфейсу IAgent
"""

import logging
from typing import Optional, Dict, Any

from .base_agent import IAgent
from .interfaces import Message, Response, UserRole

logger = logging.getLogger(__name__)


class IntelligentAgentAdapter(IAgent):
    """Адаптер для Intelligent Agent"""
    
    def __init__(self):
        self._service = None
        self._init_service()
        
    def _init_service(self):
        """Ленивая инициализация сервиса"""
        try:
            from ..services.intelligent_agent_service import intelligent_agent_service
            self._service = intelligent_agent_service
            logger.info("✅ IntelligentAgentAdapter инициализирован")
        except ImportError as e:
            logger.warning(f"⚠️ Intelligent Agent недоступен: {e}")
            
    async def process_message(self, message: Message) -> Response:
        """Обрабатывает сообщение через Intelligent Agent"""
        if not self._service:
            return Response(text="Intelligent Agent недоступен", metadata={"error": "Service not available"})
            
        return await self._service.process_message(message)
        
    async def can_handle(self, message: Message) -> bool:
        """Проверяет, может ли обработать сообщение"""
        # Intelligent Agent обрабатывает только MCP команды от администраторов бота
        from ..core.config import config
        from ..services.unified_mcp_service import unified_mcp_service
        
        # Если IntelligentAgent недоступен, не обрабатываем
        if not self._service or not self._service.is_available():
            return False
            
        # Проверяем, что пользователь админ
        if message.user.role != UserRole.ADMIN:
            return False
            
        # IntelligentAgent доступен любому администратору (не только владельцу)
        logger.debug(f"Admin user {message.user.id} can access IntelligentAgent")
            
        # Проверяем, что это MCP команда
        if not message.text:
            return False
            
        # Проверяем через unified_mcp_service или fallback для команд /mcp
        return (unified_mcp_service.is_mcp_command(message.text) or 
                message.text.startswith('/mcp') or
                message.text.startswith('/db') or 
                message.text.startswith('/docs'))
        
    def get_name(self) -> str:
        return "IntelligentAgent"
        
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
        if not self._agent:
            return Response(
                text="Извините, сервис временно недоступен",
                metadata={"error": "Agent not initialized"}
            )
            
        return await self._agent.process_message(message)
        
    async def can_handle(self, message: Message) -> bool:
        """Стандартный агент может обработать любое сообщение"""
        return self._agent is not None
        
    def get_name(self) -> str:
        return "DefaultAgent"
        
    def get_priority(self) -> int:
        return 10  # Низкий приоритет - fallback агент
        
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память пользователя"""
        if self._agent:
            return await self._agent.clear_user_memory(user_id)
        return False