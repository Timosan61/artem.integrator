"""
MCP Agent - Агент для работы с MCP через AI
"""

import json
import logging
from typing import Optional, Dict, Any, List, Tuple, Union
from datetime import datetime
import asyncio

from ...core.interfaces import Message, Response, User, UserRole
from ...core.agent import BaseAgent
from ...core.config import config
from ..handlers import MCPHandler
from .manager import MCPManager
from .interfaces import MCPFunction

logger = logging.getLogger(__name__)


class MCPAgent(BaseAgent):
    """
    Расширенный агент с поддержкой MCP
    
    Особенности:
    - Автоматическое определение MCP интента
    - Генерация функций для AI провайдеров
    - Обработка результатов MCP
    - Fallback на обычный агент
    """
    
    def __init__(self, base_agent: Optional[BaseAgent] = None):
        """
        Инициализация MCP агента
        
        Args:
            base_agent: Базовый агент для fallback
        """
        self.base_agent = base_agent
        self.mcp_enabled = config.mcp.enabled
        self.mcp_manager = None
        self.mcp_handler = None
        
        if self.mcp_enabled:
            try:
                # Инициализируем MCP компоненты
                self.mcp_manager = MCPManager()
                self.mcp_handler = MCPHandler(self.mcp_manager)
                
                # Подключаем серверы асинхронно
                asyncio.create_task(self._connect_servers())
                
                logger.info("✅ MCP Agent инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации MCP: {e}")
                self.mcp_enabled = False
    
    async def _connect_servers(self):
        """Подключает MCP серверы"""
        if self.mcp_manager:
            results = await self.mcp_manager.connect_all()
            connected = sum(1 for success in results.values() if success)
            logger.info(f"🔌 Подключено MCP серверов: {connected}/{len(results)}")
    
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает сообщение с поддержкой MCP
        
        Args:
            message: Входящее сообщение
            
        Returns:
            Response: Ответ агента
        """
        # Проверяем права доступа к MCP
        if not self._has_mcp_access(message.user):
            # Передаем обычному агенту
            if self.base_agent:
                return await self.base_agent.process_message(message)
            else:
                return Response(
                    text="MCP доступен только администраторам",
                    metadata={"mcp_access_denied": True}
                )
        
        # Проверяем MCP интент
        is_mcp, mcp_intent = await self._detect_mcp_intent(message)
        
        if is_mcp and self.mcp_enabled and self.mcp_handler:
            try:
                # Обрабатываем через MCP
                response = await self.mcp_handler.handle_message(message, mcp_intent)
                return response
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки MCP: {e}")
                # Fallback на обычный агент
                if self.base_agent:
                    return await self.base_agent.process_message(message)
                else:
                    return Response(
                        text=f"Ошибка выполнения MCP команды: {str(e)}",
                        metadata={"error": str(e)}
                    )
        
        # Обычная обработка
        if self.base_agent:
            return await self.base_agent.process_message(message)
        else:
            return Response(
                text="Базовый агент не настроен",
                metadata={"error": "No base agent"}
            )
    
    def _has_mcp_access(self, user: User) -> bool:
        """Проверяет доступ пользователя к MCP"""
        return user.role == UserRole.ADMIN
    
    async def _detect_mcp_intent(self, message: Message) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Определяет MCP интент в сообщении
        
        Returns:
            Tuple[bool, Optional[Dict]]: (является ли MCP запросом, данные интента)
        """
        text = message.text.lower()
        
        # Явные MCP команды
        if text.startswith('/mcp'):
            parts = text.split(maxsplit=2)
            if len(parts) >= 2:
                command = parts[1]
                args = parts[2] if len(parts) > 2 else ""
                
                return True, {
                    "type": "command",
                    "command": command,
                    "args": args
                }
        
        # Команда для SQL
        if text.startswith('/db'):
            query = text[3:].strip()
            return True, {
                "type": "sql",
                "query": query
            }
        
        # Команда для документации
        if text.startswith('/docs'):
            parts = text.split(maxsplit=2)
            if len(parts) >= 2:
                return True, {
                    "type": "docs",
                    "library": parts[1],
                    "topic": parts[2] if len(parts) > 2 else None
                }
        
        # Анализ естественного языка для MCP интента
        mcp_keywords = {
            "supabase": ["база данн", "таблиц", "sql", "миграци", "supabase"],
            "digitalocean": ["деплой", "приложени", "digitalocean", "сервер"],
            "context7": ["документаци", "пример", "как использовать", "api"]
        }
        
        for server, keywords in mcp_keywords.items():
            if any(keyword in text for keyword in keywords):
                return True, {
                    "type": "natural",
                    "server": server,
                    "query": text
                }
        
        return False, None
    
    async def get_available_functions(self) -> List[MCPFunction]:
        """Получает список доступных MCP функций"""
        if self.mcp_manager:
            return await self.mcp_manager.get_available_functions()
        return []
    
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память пользователя"""
        # Очищаем кеш MCP для пользователя
        if self.mcp_manager:
            # TODO: Реализовать очистку кеша по user_id
            pass
        
        # Передаем базовому агенту
        if self.base_agent:
            return await self.base_agent.clear_user_memory(user_id)
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Получает статус агента"""
        status = {
            "mcp_enabled": self.mcp_enabled,
            "base_agent": self.base_agent is not None
        }
        
        if self.mcp_manager:
            status["mcp_status"] = self.mcp_manager.get_status()
        
        if self.base_agent and hasattr(self.base_agent, 'get_status'):
            status["base_agent_status"] = self.base_agent.get_status()
        
        return status
    
    async def shutdown(self):
        """Корректное завершение работы"""
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
        
        if self.base_agent and hasattr(self.base_agent, 'shutdown'):
            await self.base_agent.shutdown()