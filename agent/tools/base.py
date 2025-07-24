"""
Базовый класс для всех инструментов
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type
from pydantic import BaseModel
import logging

from ..core.models import BaseToolParams, ToolResponse, ToolType

logger = logging.getLogger(__name__)


class ToolMetadata(BaseModel):
    """Метаданные инструмента"""
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Intelligent Agent"
    requires_confirmation: bool = False
    estimated_time: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


class BaseTool(ABC):
    """Базовый класс для всех инструментов"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"🔧 Инструмент {self.__class__.__name__} инициализирован")
    
    @abstractmethod
    def get_metadata(self) -> ToolMetadata:
        """Возвращает метаданные инструмента"""
        pass
    
    @abstractmethod
    def get_openai_schema(self) -> Dict[str, Any]:
        """Возвращает схему функции для OpenAI"""
        pass
    
    @abstractmethod
    def get_params_model(self) -> Type[BaseToolParams]:
        """Возвращает Pydantic модель параметров"""
        pass
    
    @abstractmethod
    async def execute(self, params: BaseToolParams) -> ToolResponse:
        """
        Выполняет инструмент
        
        Args:
            params: Валидированные параметры
            
        Returns:
            ToolResponse с результатом выполнения
        """
        pass
    
    def validate_params(self, params_dict: Dict[str, Any]) -> BaseToolParams:
        """
        Валидирует параметры через Pydantic
        
        Args:
            params_dict: Словарь параметров
            
        Returns:
            Валидированные параметры
            
        Raises:
            ValidationError: Если параметры невалидны
        """
        params_model = self.get_params_model()
        return params_model(**params_dict)
    
    async def execute_with_validation(self, params_dict: Dict[str, Any]) -> ToolResponse:
        """
        Валидирует параметры и выполняет инструмент
        
        Args:
            params_dict: Словарь параметров
            
        Returns:
            ToolResponse с результатом
        """
        try:
            # Валидируем параметры
            validated_params = self.validate_params(params_dict)
            
            # Логируем выполнение
            self.logger.info(
                f"🚀 Выполнение {self.metadata.name} для пользователя {validated_params.user_id}"
            )
            
            # Выполняем инструмент
            result = await self.execute(validated_params)
            
            # Добавляем метаданные
            if result.metadata is None:
                result.metadata = {}
            result.metadata["tool_name"] = self.metadata.name
            result.metadata["tool_version"] = self.metadata.version
            
            if result.success:
                self.logger.info(f"✅ {self.metadata.name} выполнен успешно")
            else:
                self.logger.error(f"❌ {self.metadata.name} завершился с ошибкой: {result.error}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка выполнения {self.metadata.name}: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=str(e),
                metadata={"tool_name": self.metadata.name}
            )
    
    def get_confirmation_message(self, params: BaseToolParams) -> Optional[str]:
        """
        Возвращает сообщение для подтверждения действия
        
        Args:
            params: Параметры инструмента
            
        Returns:
            Сообщение для подтверждения или None
        """
        if not self.metadata.requires_confirmation:
            return None
        
        message = f"""
📋 **Подтверждение действия**

Инструмент: **{self.metadata.name}**
{self.metadata.description}

"""
        
        if self.metadata.estimated_time:
            message += f"⏱ Время выполнения: {self.metadata.estimated_time}\n\n"
        
        message += "Подтвердить выполнение?\n✅ Да / ❌ Нет"
        
        return message