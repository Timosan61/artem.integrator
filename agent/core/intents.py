"""
Определение типов намерений (Intent) для агента
"""
from enum import Enum


class Intent(str, Enum):
    """Типы намерений пользователя"""
    MCP_COMMAND = "mcp_command"
    IMAGE_GENERATION = "image_generation"
    YOUTUBE_ANALYSIS = "youtube_analysis"
    GENERAL_QUESTION = "general_question"
    GENERAL_CHAT = "general_chat"
    CLARIFICATION_NEEDED = "clarification_needed"
    UNKNOWN = "unknown"