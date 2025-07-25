"""
Упрощенные намерения для Simple Agent
"""
from enum import Enum


class Intent(Enum):
    """Базовые намерения пользователя"""
    
    # Основные типы намерений
    MCP_COMMAND = "mcp_command"
    YOUTUBE_ANALYSIS = "youtube_analysis" 
    IMAGE_GENERATION = "image_generation"
    GENERAL_CHAT = "general_chat"
    
    # Служебные
    CLARIFICATION_NEEDED = "clarification_needed"
    
    @property
    def value(self) -> str:
        """Возвращает строковое значение намерения"""
        return self._value_