"""
Echo Tool - простой инструмент для тестирования
"""
from typing import Dict, Any, Type

from .base import BaseTool, ToolMetadata
from ..core.models import BaseToolParams, ToolResponse, EchoToolParams, ToolType


class EchoTool(BaseTool):
    """Инструмент для эхо-ответов (тестирование)"""
    
    @property
    def metadata(self) -> ToolMetadata:
        """Свойство для совместимости с ToolRegistry"""
        return self.get_metadata()
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="echo_tool",
            description="Простой инструмент для тестирования, который возвращает эхо сообщения",
            version="1.0.0",
            requires_confirmation=False
        )
    
    def get_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "echo_tool",
                "description": self.metadata.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "description": "Сообщение для эхо-ответа"
                        },
                        "uppercase": {
                            "type": "boolean",
                            "description": "Вернуть в верхнем регистре",
                            "default": False
                        },
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        }
                    },
                    "required": ["message", "user_id"]
                }
            }
        }
    
    def get_params_model(self) -> Type[BaseToolParams]:
        return EchoToolParams
    
    async def execute(self, params: EchoToolParams) -> ToolResponse:
        """Выполняет эхо"""
        try:
            result = params.message
            if params.uppercase:
                result = result.upper()
            
            self.logger.debug(f"Echo: '{params.message}' -> '{result}'")
            
            return ToolResponse(
                success=True,
                data={
                    "echo": result,
                    "original": params.message,
                    "uppercase": params.uppercase
                },
                metadata={
                    "tool_type": ToolType.ECHO,
                    "message_length": len(params.message)
                }
            )
        except Exception as e:
            return ToolResponse(
                success=False,
                error=f"Ошибка выполнения echo: {str(e)}",
                metadata={"tool_type": ToolType.ECHO}
            )