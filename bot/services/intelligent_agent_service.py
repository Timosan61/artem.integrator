"""
Сервис интеграции Simple Agent с Telegram ботом
Упрощенная архитектура без MCPTool и ToolRegistry
"""
import logging
import os
from typing import Dict, Any, Optional

from agent.core.intelligent_agent import IntelligentAgent
from ..core.interfaces import Message, Response, UserRole
from ..core.config import config

logger = logging.getLogger(__name__)


class IntelligentAgentService:
    """Сервис для работы с Simple Agent (упрощенная архитектура)"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.enabled = False
        self.agent = None
        
        # Проверяем наличие API ключей
        openai_key = config.openai.api_key or os.getenv("OPENAI_API_KEY")
        anthropic_key = config.anthropic.api_key or os.getenv("ANTHROPIC_API_KEY")
        
        if not openai_key:
            logger.warning("⚠️ OpenAI API key не найден - Simple Agent отключен")
            return
            
        try:
            # Создаем агента с поддержкой нескольких провайдеров
            self.agent = IntelligentAgent(
                api_key=openai_key, 
                model="gpt-4o",
                anthropic_api_key=anthropic_key
            )
            self.enabled = True
            
            # Логируем доступные провайдеры
            providers = []
            if openai_key:
                providers.append("OpenAI")
            if anthropic_key:
                providers.append("Anthropic")
            if hasattr(self.agent, 'claude_code_service') and self.agent.claude_code_service:
                providers.append("Claude SDK")
                
            logger.info(f"✅ Simple Agent Service инициализирован с провайдерами: {', '.join(providers)}")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Simple Agent: {e}")
    
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает сообщение через Simple Agent
        
        Args:
            message: Сообщение от пользователя
            
        Returns:
            Response от агента
        """
        if not self.enabled or not self.agent:
            return Response(
                text="❌ Simple Agent не доступен"
            )
        
        try:
            # Обрабатываем сообщение через упрощенного агента
            agent_response = await self.agent.process_message(
                message=message.text,
                user_id=str(message.user.id)
            )
            
            # Формируем ответ
            response_text = agent_response.message
            
            # Добавляем технические детали если есть
            metadata = {
                "success": True,
                "agent_type": "simple_agent"
            }
            
            # Добавляем информацию об инструменте если использовался
            if hasattr(agent_response, 'tool_used') and agent_response.tool_used:
                tool_info = f"\n\n_🔧 Использован: {agent_response.tool_used.value}_"
                response_text += tool_info
                metadata["tool_used"] = agent_response.tool_used.value
            
            # Добавляем информацию о confidence если доступна
            if hasattr(agent_response, 'confidence') and agent_response.confidence < 0.7:
                confidence_info = f"\n\n_⚠️ Уверенность: {agent_response.confidence:.0%}_"
                response_text += confidence_info
                metadata["confidence"] = agent_response.confidence
            
            return Response(
                text=response_text,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения Simple Agent: {e}", exc_info=True)
            return Response(
                text=f"❌ Ошибка обработки: {str(e)}",
                metadata={"success": False, "agent_type": "simple_agent"}
            )
    
    def is_available(self) -> bool:
        """Проверяет доступность сервиса"""
        return self.enabled and self.agent is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        return {
            "enabled": self.enabled,
            "available": self.is_available(),
            "agent_type": "simple_agent",
            "model": "gpt-4o" if self.agent else None
        }


# Создаем глобальный экземпляр сервиса
intelligent_agent_service = IntelligentAgentService()


__all__ = ['intelligent_agent_service']