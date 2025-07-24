"""
Pydantic модели для Intelligent Agent
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

from .intents import Intent


class ToolType(str, Enum):
    """Типы доступных инструментов"""
    MCP = "mcp_executor"
    YOUTUBE_ANALYZER = "youtube_analyzer"
    IMAGE_GENERATOR = "image_generator"
    ECHO = "echo_tool"  # для тестирования


class BaseToolParams(BaseModel):
    """Базовые параметры для всех инструментов"""
    user_id: str = Field(description="ID пользователя, выполняющего запрос")
    
    class Config:
        extra = "allow"  # Разрешаем дополнительные поля


class EchoToolParams(BaseToolParams):
    """Параметры для тестового echo инструмента"""
    message: str = Field(description="Сообщение для эхо-ответа")
    uppercase: bool = Field(default=False, description="Вернуть в верхнем регистре")


class MCPCommandParams(BaseToolParams):
    """Параметры для MCP команды"""
    command: str = Field(description="MCP команда для выполнения (например: 'list apps', 'show databases')")
    filters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Дополнительные фильтры для команды"
    )


class ImageGenerationParams(BaseToolParams):
    """Параметры для генерации изображения"""
    prompt: str = Field(
        description="Детальное описание желаемого изображения на английском языке"
    )
    style: str = Field(
        default="realistic",
        description="Стиль изображения: realistic, cartoon, abstract, oil-painting, watercolor"
    )
    size: str = Field(
        default="1024x1024",
        description="Размер изображения: 1024x1024, 1792x1024, 1024x1792"
    )
    quality: str = Field(
        default="standard",
        description="Качество: standard или hd"
    )


class YouTubeAnalysisParams(BaseToolParams):
    """Параметры для анализа YouTube видео"""
    url: str = Field(description="URL YouTube видео для анализа")
    extract_subtitles: bool = Field(
        default=True,
        description="Извлечь субтитры видео (если доступны)"
    )
    subtitle_language: Optional[str] = Field(
        default="ru",
        description="Предпочитаемый язык субтитров (ru, en, auto)"
    )
    include_metadata: bool = Field(
        default=True,
        description="Включить метаданные видео (название, описание, статистика)"
    )


class ToolResponse(BaseModel):
    """Ответ от инструмента"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        arbitrary_types_allowed = True


class AgentResponse(BaseModel):
    """Ответ от агента"""
    message: str
    tool_used: Optional[ToolType] = None
    tool_response: Optional[ToolResponse] = None
    requires_confirmation: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    intent: Optional[Intent] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ConfirmationRequest(BaseModel):
    """Запрос подтверждения действия"""
    tool_name: str
    tool_description: str
    estimated_time: str
    details: List[str]
    alternatives: Optional[List[Dict[str, str]]] = None
    

class ConversationState(BaseModel):
    """Состояние разговора с пользователем"""
    user_id: str
    state_type: str  # "confirmation", "clarification", "normal"
    original_message: str
    tool_to_execute: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None


class UserPreference(BaseModel):
    """Предпочтения пользователя"""
    user_id: str
    pattern: str
    preferred_tool: ToolType
    confidence_threshold: float = 0.8
    usage_count: int = 0
    last_used: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)