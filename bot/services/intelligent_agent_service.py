"""
Сервис интеграции Intelligent Agent с Telegram ботом
"""
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from agent.core.intelligent_agent import IntelligentAgent
from agent.core.tool_registry import ToolRegistry
from agent.core.confirmation_manager import ConfirmationManager
from agent.tools.mcp_tool import MCPTool
from agent.tools.youtube_tool import YouTubeAnalyzerTool
from ..core.interfaces import Message, Response, UserRole
from ..core.config import config

logger = logging.getLogger(__name__)


class IntelligentAgentService:
    """Сервис для работы с Intelligent Agent"""
    
    def __init__(self):
        """Инициализация сервиса"""
        self.enabled = False
        self.agent = None
        self.tool_registry = None
        self.confirmation_manager = None
        
        # Проверяем наличие OpenAI API ключа
        openai_key = config.openai.api_key or os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("⚠️ OpenAI API key не найден - Intelligent Agent отключен")
            return
            
        try:
            # Инициализируем компоненты
            self._initialize_components(openai_key)
            self.enabled = True
            logger.info("✅ Intelligent Agent Service инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Intelligent Agent: {e}")
    
    def _initialize_components(self, api_key: str):
        """Инициализирует все компоненты агента"""
        # Создаем агента
        self.agent = IntelligentAgent(api_key=api_key, model="gpt-4o")
        
        # Используем реестр инструментов агента
        self.tool_registry = self.agent.tool_registry
        
        # Регистрируем инструменты
        self._register_tools()
        
        # Создаем менеджер подтверждений
        self.confirmation_manager = ConfirmationManager()
    
    def _register_tools(self):
        """Регистрирует доступные инструменты"""
        # MCP Tool
        mcp_tool = MCPTool()
        self.tool_registry.register_tool(mcp_tool)
        
        # YouTube Tool
        youtube_api_key = os.getenv("YOUTUBE_API_KEY")
        if youtube_api_key:
            youtube_tool = YouTubeAnalyzerTool(api_key=youtube_api_key)
            self.tool_registry.register_tool(youtube_tool)
            logger.info("✅ YouTube Analyzer Tool зарегистрирован")
        else:
            logger.warning("⚠️ YouTube API key не найден - YouTube Analyzer отключен")
    
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает сообщение через Intelligent Agent
        
        Args:
            message: Сообщение от пользователя
            
        Returns:
            Response от агента
        """
        if not self.enabled or not self.agent:
            return Response(
                text="❌ Intelligent Agent не доступен"
            )
        
        try:
            # Проверяем состояние подтверждения
            pending_sessions = self.confirmation_manager.get_pending_sessions(str(message.user.id))
            confirmation_state = pending_sessions[0] if pending_sessions else None
            
            if confirmation_state:
                # Обрабатываем ответ на подтверждение
                return await self._handle_confirmation_response(message, confirmation_state)
            
            # Получаем контекст из памяти
            context = await self._get_user_context(message.user.id)
            
            # Обрабатываем через агента
            agent_response = await self.agent.process_message(
                message=message.text,
                user_id=str(message.user.id),
                context=context
            )
            
            # Проверяем необходимость подтверждения
            if agent_response.requires_confirmation:
                return await self._handle_confirmation_request(
                    message, 
                    agent_response
                )
            
            # Формируем ответ
            response_text = agent_response.message
            
            # Добавляем информацию об использованном инструменте
            if agent_response.tool_used:
                tool_info = f"\n\n_🔧 Использован: {agent_response.tool_used.value}_"
                response_text += tool_info
            
            # Добавляем информацию о confidence если низкая
            if agent_response.confidence < 0.7:
                confidence_info = f"\n\n_⚠️ Уверенность: {agent_response.confidence:.0%}_"
                response_text += confidence_info
            
            return Response(
                text=response_text,
                metadata={
                    "intent": agent_response.intent.value if agent_response.intent else None,
                    "tool_used": agent_response.tool_used.value if agent_response.tool_used else None,
                    "confidence": agent_response.confidence,
                    "success": True
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return Response(
                text=f"❌ Ошибка обработки: {str(e)}",
                metadata={"success": False}
            )
    
    async def _get_user_context(self, user_id: int) -> Optional[list]:
        """Получает контекст пользователя из памяти"""
        # TODO: Интеграция с MemoryManager
        return None
    
    async def _handle_confirmation_request(
        self, 
        message: Message, 
        agent_response
    ) -> Response:
        """Обрабатывает запрос подтверждения"""
        # Создаем состояние подтверждения
        session_id = self.confirmation_manager.create_confirmation(
            user_id=str(message.user.id),
            tool_name=agent_response.tool_used.value,
            tool_params=agent_response.tool_response.data if agent_response.tool_response else {},
            original_message=message.text
        )
        
        # Форматируем сообщение подтверждения
        confirmation_text = agent_response.message
        confirmation_text += "\n\n✅ Да / ❌ Нет"
        
        return Response(
            text=confirmation_text,
            metadata={
                "confirmation_required": True,
                "session_id": session_id,
                "success": True
            }
        )
    
    async def _handle_confirmation_response(
        self, 
        message: Message, 
        confirmation_state
    ) -> Response:
        """Обрабатывает ответ на подтверждение"""
        user_response = message.text.lower().strip()
        
        # Проверяем ответ
        if user_response in ['да', 'yes', '✅', 'подтверждаю', 'ok']:
            # Выполняем подтвержденное действие
            tool = self.tool_registry.get_tool(confirmation_state.tool_name)
            if tool:
                try:
                    result = await tool.execute(confirmation_state.parameters)
                    # Очищаем сессию подтверждения
                    for session in self.confirmation_manager.get_pending_sessions(str(message.user.id)):
                        self.confirmation_manager.cancel_session(session.session_id)
                    
                    if result.success:
                        return Response(
                            text=f"✅ {result.data.get('message', 'Операция выполнена успешно')}",
                            metadata={"success": True}
                        )
                    else:
                        return Response(
                            text=f"❌ Ошибка выполнения: {result.error}",
                            metadata={"success": False}
                        )
                except Exception as e:
                    logger.error(f"❌ Ошибка выполнения инструмента: {e}")
                    return Response(
                        text=f"❌ Ошибка выполнения: {str(e)}",
                        metadata={"success": False}
                    )
            else:
                return Response(
                    text="❌ Инструмент не найден",
                    metadata={"success": False}
                )
        elif user_response in ['нет', 'no', '❌', 'отмена', 'cancel']:
            # Отменяем операцию
            self.confirmation_manager.clear_user_state(str(message.user.id))
            return Response(
                text="❌ Операция отменена",
                metadata={"success": True}
            )
        else:
            # Неизвестный ответ
            return Response(
                text="❓ Пожалуйста, ответьте Да или Нет",
                metadata={"success": True}
            )
    
    def is_available(self) -> bool:
        """Проверяет доступность сервиса"""
        return self.enabled and self.agent is not None
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус сервиса"""
        stats = self.confirmation_manager.get_session_stats() if self.confirmation_manager else {}
        return {
            "enabled": self.enabled,
            "available": self.is_available(),
            "tools": self.tool_registry.list_tools() if self.tool_registry else [],
            "active_confirmations": stats.get("active_sessions", 0)
        }


# Создаем глобальный экземпляр сервиса
intelligent_agent_service = IntelligentAgentService()


__all__ = ['intelligent_agent_service']