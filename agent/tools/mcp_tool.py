"""
MCP Tool - интеграция с Claude Code SDK для выполнения MCP команд
"""
import os
import sys
from typing import Dict, Any, Type
from pathlib import Path

# Добавляем корневую директорию в path для импорта
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from .base import BaseTool, ToolMetadata
from ..core.models import BaseToolParams, ToolResponse, MCPCommandParams, ToolType

# Импортируем существующий ClaudeCodeService
try:
    from bot.services.claude_code_service import claude_code_service
    CLAUDE_SERVICE_AVAILABLE = True
except ImportError:
    claude_code_service = None
    CLAUDE_SERVICE_AVAILABLE = False


class MCPTool(BaseTool):
    """Инструмент для выполнения MCP команд через Claude Code SDK"""
    
    def __init__(self):
        super().__init__()
        if not CLAUDE_SERVICE_AVAILABLE:
            self.logger.warning("⚠️ ClaudeCodeService недоступен, MCP команды будут эмулироваться")
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="mcp_executor",
            description="Выполняет MCP команды для управления инфраструктурой (приложения, базы данных, серверы) через Claude Code SDK",
            version="1.0.0",
            requires_confirmation=True,
            estimated_time="5-30 секунд"
        )
    
    @property
    def metadata(self) -> ToolMetadata:
        """Свойство для совместимости с ToolRegistry"""
        return self.get_metadata()
    
    def get_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "execute_mcp_command",
                "description": self.metadata.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "MCP команда (например: 'list apps', 'show databases', 'get deployments')"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        },
                        "filters": {
                            "type": "object",
                            "description": "Дополнительные фильтры для команды",
                            "default": {}
                        }
                    },
                    "required": ["command", "user_id"]
                }
            }
        }
    
    def get_params_model(self) -> Type[BaseToolParams]:
        return MCPCommandParams
    
    async def execute(self, params: MCPCommandParams) -> ToolResponse:
        """Выполняет MCP команду"""
        try:
            # Форматируем команду для ClaudeCodeService
            formatted_command = self._format_command(params.command)
            
            if CLAUDE_SERVICE_AVAILABLE and claude_code_service:
                # Выполняем через реальный сервис
                self.logger.info(f"🔌 Выполнение MCP команды: {formatted_command}")
                
                result = await claude_code_service.execute_mcp_command(
                    formatted_command,
                    params.user_id
                )
                
                if result.get("success"):
                    return ToolResponse(
                        success=True,
                        data={
                            "command": formatted_command,
                            "response": result.get("response", "Команда выполнена"),
                            "mcp_response": result.get("data") or result.get("mcp_response")
                        },
                        metadata={
                            "tool_type": ToolType.MCP,
                            "command_type": self._get_command_type(params.command),
                            "execution_time": result.get("execution_time")
                        }
                    )
                else:
                    return ToolResponse(
                        success=False,
                        error=result.get("error", "Неизвестная ошибка MCP"),
                        metadata={"tool_type": ToolType.MCP}
                    )
            else:
                # Эмуляция для тестирования
                return self._emulate_mcp_response(params)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка выполнения MCP команды: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=f"Ошибка выполнения MCP: {str(e)}",
                metadata={"tool_type": ToolType.MCP}
            )
    
    def _format_command(self, command: str) -> str:
        """Форматирует команду для ClaudeCodeService"""
        command_lower = command.lower()
        
        # Мапинг естественных команд на MCP команды
        command_mappings = {
            "list apps": "/mcp apps",
            "show apps": "/mcp apps",
            "приложения": "/mcp apps",
            "show databases": "/db SELECT datname FROM pg_database",
            "list databases": "/db SELECT datname FROM pg_database", 
            "базы данных": "/db SELECT datname FROM pg_database",
            "get deployments": "/mcp apps",
            "деплойменты": "/mcp apps"
        }
        
        # Проверяем прямые мапинги
        for key, mcp_command in command_mappings.items():
            if key in command_lower:
                return mcp_command
        
        # Если команда уже начинается с /, возвращаем как есть
        if command.startswith('/'):
            return command
        
        # Иначе добавляем префикс /mcp
        return f"/mcp {command}"
    
    def _get_command_type(self, command: str) -> str:
        """Определяет тип команды"""
        command_lower = command.lower()
        
        if any(word in command_lower for word in ["app", "приложен"]):
            return "applications"
        elif any(word in command_lower for word in ["database", "db", "база", "баз данных", "базы данных"]):
            return "databases"
        elif any(word in command_lower for word in ["deploy", "деплой"]):
            return "deployments"
        else:
            return "general"
    
    def _emulate_mcp_response(self, params: MCPCommandParams) -> ToolResponse:
        """Эмулирует ответ MCP для тестирования"""
        command_type = self._get_command_type(params.command)
        
        emulated_responses = {
            "applications": {
                "apps": [
                    {"name": "web-app", "region": "nyc3", "status": "active"},
                    {"name": "api-service", "region": "sfo2", "status": "active"}
                ]
            },
            "databases": {
                "databases": [
                    {"name": "production_db", "engine": "postgres", "version": "14"},
                    {"name": "analytics_db", "engine": "postgres", "version": "13"}
                ]
            },
            "deployments": {
                "deployments": [
                    {"id": "dep-123", "status": "success", "created_at": "2024-01-20"},
                    {"id": "dep-124", "status": "in_progress", "created_at": "2024-01-21"}
                ]
            }
        }
        
        response_data = emulated_responses.get(
            command_type,
            {"message": f"Эмулированный ответ для команды: {params.command}"}
        )
        
        return ToolResponse(
            success=True,
            data={
                "command": params.command,
                "response": f"[ЭМУЛЯЦИЯ] Результаты для {command_type}",
                "mcp_response": response_data
            },
            metadata={
                "tool_type": ToolType.MCP,
                "command_type": command_type,
                "emulated": True
            }
        )
    
    def get_confirmation_message(self, params: MCPCommandParams) -> str:
        """Возвращает сообщение для подтверждения MCP команды"""
        command_type = self._get_command_type(params.command)
        
        details = {
            "applications": [
                "📱 Получение списка приложений",
                "📊 Статус деплойментов",
                "🔧 Конфигурация сервисов"
            ],
            "databases": [
                "🗄 Список баз данных",
                "📊 Статистика использования",
                "🔐 Информация о доступах"
            ],
            "deployments": [
                "🚀 История деплойментов",
                "📈 Статус выполнения",
                "⚙️ Конфигурация релизов"
            ]
        }
        
        message = f"""
📋 **Подтверждение MCP команды**

Команда: **{params.command}**
Тип: **{command_type}**

Будет выполнено:
"""
        
        for detail in details.get(command_type, ["📊 Выполнение MCP команды"]):
            message += f"• {detail}\n"
        
        message += f"\n⏱ Время выполнения: {self.metadata.estimated_time}\n\n"
        message += "Подтвердить выполнение?\n✅ Да / ❌ Нет"
        
        return message