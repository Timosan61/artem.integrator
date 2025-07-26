"""
Унифицированный MCP сервис

Централизует всю MCP функциональность в одном месте
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

try:
    from ..core.logging_utils import (
        get_structured_logger, ComponentType, TraceContext,
        log_operation_start, log_operation_success, log_operation_error
    )
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False

from ..core.config import config
from ..core.errors import MCPError
from ..formatters.mcp_formatter import MCPFormatter

logger = logging.getLogger(__name__)

# Инициализируем структурированный логгер если доступен
if STRUCTURED_LOGGING:
    structured_logger = get_structured_logger("unified_mcp_service", ComponentType.MCP)
else:
    structured_logger = None


class MCPProvider(str, Enum):
    """Доступные MCP провайдеры"""
    CLAUDE_SDK = "claude_sdk"
    DIGITALOCEAN = "digitalocean"
    CONTEXT7 = "context7"
    SUPABASE = "supabase"
    CLOUDFLARE = "cloudflare"


@dataclass
class MCPCommand:
    """Структура MCP команды"""
    provider: MCPProvider
    action: str
    params: Dict[str, Any]
    raw_text: Optional[str] = None


class UnifiedMCPService:
    """
    Единый сервис для работы с MCP
    
    Объединяет:
    - Claude Code SDK для выполнения команд
    - Парсинг и определение MCP команд
    - Форматирование результатов
    - Обработку ошибок
    """
    
    def __init__(self):
        self.formatter = MCPFormatter()
        self._claude_sdk_available = False
        self.structured_logger = structured_logger if STRUCTURED_LOGGING else None
        self._init_claude_sdk()
        
    def _init_claude_sdk(self):
        """Инициализация Claude Code SDK"""
        try:
            from claude_code_sdk import claude_code_execute_mcp_tool
            self._claude_sdk_available = True
            logger.info("✅ Claude Code SDK инициализирован")
        except ImportError:
            logger.warning("⚠️ Claude Code SDK недоступен - MCP команды будут эмулироваться")
            
    def parse_mcp_command(self, text: str) -> Optional[MCPCommand]:
        """
        Парсит текст и определяет MCP команду
        
        Примеры:
        - /mcp apps list -> MCPCommand(provider=DIGITALOCEAN, action="list_apps")
        - покажи приложения -> MCPCommand(provider=DIGITALOCEAN, action="list_apps")
        """
        text_lower = text.lower().strip()
        
        # Прямые MCP команды
        if text_lower.startswith('/mcp'):
            parts = text_lower.split()
            if len(parts) >= 3:
                provider_hint = parts[1]
                action = parts[2]
                
                # Определяем провайдера
                if provider_hint in ['apps', 'app', 'do', 'digitalocean']:
                    return MCPCommand(
                        provider=MCPProvider.DIGITALOCEAN,
                        action=f"{action}_apps" if not action.endswith('apps') else action,
                        params={},
                        raw_text=text
                    )
                elif provider_hint in ['context', 'context7', 'ctx']:
                    return MCPCommand(
                        provider=MCPProvider.CONTEXT7,
                        action=action,
                        params={},
                        raw_text=text
                    )
                    
        # Естественный язык
        if any(word in text_lower for word in ['приложения', 'apps', 'апп', 'application']):
            if any(word in text_lower for word in ['покажи', 'список', 'list', 'show']):
                return MCPCommand(
                    provider=MCPProvider.DIGITALOCEAN,
                    action="list_apps",
                    params={},
                    raw_text=text
                )
                
        return None
        
    async def execute_command(self, command: MCPCommand) -> Dict[str, Any]:
        """
        Выполняет MCP команду
        
        Returns:
            Dict с результатом выполнения
        """
        try:
            if self._claude_sdk_available:
                return await self._execute_via_sdk(command)
            else:
                return await self._emulate_command(command)
                
        except Exception as e:
            logger.error(f"Ошибка выполнения MCP команды: {e}")
            raise MCPError(f"Ошибка выполнения команды: {str(e)}")
            
    async def _execute_via_sdk(self, command: MCPCommand) -> Dict[str, Any]:
        """Выполнение через Claude Code SDK"""
        try:
            from claude_code_sdk import claude_code_execute_mcp_tool
            
            # Маппинг команд на MCP функции
            mcp_function_map = {
                (MCPProvider.DIGITALOCEAN, "list_apps"): "mcp__digitalocean__list_apps",
                (MCPProvider.DIGITALOCEAN, "get_app"): "mcp__digitalocean__get_app",
                (MCPProvider.CONTEXT7, "search"): "mcp__context7__search",
            }
            
            mcp_function = mcp_function_map.get((command.provider, command.action))
            if not mcp_function:
                return {
                    "success": False,
                    "error": f"Неизвестная команда: {command.action} для {command.provider}"
                }
                
            # Выполняем через SDK
            result = await asyncio.to_thread(
                claude_code_execute_mcp_tool,
                mcp_function,
                command.params
            )
            
            return {
                "success": True,
                "data": result,
                "provider": command.provider.value,
                "action": command.action
            }
            
        except Exception as e:
            logger.error(f"SDK error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    async def _emulate_command(self, command: MCPCommand) -> Dict[str, Any]:
        """Эмуляция выполнения команды (для отладки)"""
        logger.info(f"📋 Эмуляция MCP команды: {command.provider} -> {command.action}")
        
        if command.provider == MCPProvider.DIGITALOCEAN and command.action == "list_apps":
            return {
                "success": True,
                "data": {
                    "apps": [
                        {
                            "id": "demo-app-1",
                            "name": "artem-webhook-bot",
                            "status": "active",
                            "created_at": "2024-01-15T10:00:00Z",
                            "region": "fra1"
                        },
                        {
                            "id": "demo-app-2", 
                            "name": "test-deployment",
                            "status": "inactive",
                            "created_at": "2024-01-10T15:30:00Z",
                            "region": "ams3"
                        }
                    ]
                },
                "provider": command.provider.value,
                "action": command.action,
                "emulated": True
            }
            
        return {
            "success": False,
            "error": "Команда не поддерживается в режиме эмуляции"
        }
        
    def format_result(self, result: Dict[str, Any]) -> str:
        """Форматирует результат для отображения пользователю"""
        if not result.get("success"):
            return f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}"
            
        # Используем форматтер для красивого вывода
        return self.formatter.format_mcp_result(result)
        
    async def process_message(self, text: str) -> Optional[str]:
        """
        Обрабатывает сообщение и выполняет MCP команду если найдена
        
        Returns:
            Отформатированный результат или None если не MCP команда
        """
        command = self.parse_mcp_command(text)
        if not command:
            return None
            
        try:
            result = await self.execute_command(command)
            return self.format_result(result)
        except MCPError as e:
            return f"❌ {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in MCP processing: {e}")
            return "❌ Произошла неожиданная ошибка при обработке команды"
            
    def is_mcp_command(self, text: str) -> bool:
        """Быстрая проверка - является ли текст MCP командой"""
        return self.parse_mcp_command(text) is not None


# Глобальный экземпляр сервиса
unified_mcp_service = UnifiedMCPService()