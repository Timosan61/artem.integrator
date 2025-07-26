"""
Упрощенный унифицированный агент

Прямой вызов Claude Code SDK для обработки естественного языка
по аналогии с Claude Desktop
"""

import logging
from typing import Optional

from .interfaces import Message, Response
from ..services.claude_code_service import claude_code_service

logger = logging.getLogger(__name__)


class UnifiedAgent:
    """
    Упрощенный агент с прямым вызовом Claude Code SDK
    
    Повторяет логику Claude Desktop:
    - Получает естественный язык от пользователя
    - Передает напрямую в Claude Code SDK
    - SDK сам анализирует схемы MCP и вызывает нужные функции
    """
    
    def __init__(self):
        """Инициализация сервиса"""
        self.claude_service = claude_code_service
        logger.info("✅ UnifiedAgent инициализирован с Claude Code SDK")
        
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает сообщение через Claude Code SDK
        
        Args:
            message: Сообщение для обработки
            
        Returns:
            Response от Claude Code SDK
        """
        logger.info(f"📨 UnifiedAgent: сообщение от {message.user.id} -> Claude Code SDK")
        
        try:
            # Передаем естественный язык напрямую в Claude Code SDK
            result = await self.claude_service.execute_natural_request(
                text=message.text,
                user_id=str(message.user.id)
            )
            
            if result.get("success"):
                logger.info("✅ Claude Code SDK успешно обработал сообщение")
                return Response(
                    text=result.get("response", "Выполнено"),
                    metadata={
                        "agent": "ClaudeCodeSDK",
                        "success": True
                    }
                )
            else:
                logger.warning(f"⚠️ Claude Code SDK вернул ошибку: {result.get('error')}")
                return Response(
                    text=f"Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                    metadata={
                        "agent": "ClaudeCodeSDK", 
                        "success": False,
                        "error": result.get("error")
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ Ошибка вызова Claude Code SDK: {e}", exc_info=True)
            return Response(
                text="Извините, произошла ошибка при обработке сообщения.",
                metadata={"error": str(e), "agent": "UnifiedAgent"}
            )
            
    async def clear_user_memory(self, user_id: int) -> bool:
        """
        Заглушка для совместимости - Claude Code SDK не сохраняет историю
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True всегда
        """
        logger.info(f"🧹 Очистка памяти пользователя {user_id} (заглушка - SDK без истории)")
        return True
        
    def get_status(self) -> dict:
        """
        Возвращает статус Claude Code SDK
        
        Returns:
            Словарь со статусом системы
        """
        return {
            "agent": "ClaudeCodeSDK",
            "enabled": self.claude_service.enabled,
            "mcp_config": str(self.claude_service.mcp_config_path),
            "api_key_set": bool(self.claude_service.api_key)
        }
        
    async def get_agent_for_message(self, message: Message) -> Optional[str]:
        """
        Всегда возвращает Claude Code SDK как единственный агент
        
        Args:
            message: Сообщение для анализа
            
        Returns:
            Имя агента
        """
        return "ClaudeCodeSDK"


# Глобальный экземпляр унифицированного агента
unified_agent = UnifiedAgent()