"""
Confirmation Formatter - форматирование сообщений подтверждения
"""
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..core.models import ToolType, BaseToolParams
from ..tools.base import BaseTool


class ConfirmationFormatter:
    """Форматтер для создания красивых сообщений подтверждения"""
    
    # Эмодзи для разных типов инструментов
    TOOL_EMOJIS = {
        ToolType.MCP: "🔧",
        ToolType.IMAGE_GENERATOR: "🎨",
        ToolType.VISION_ANALYZER: "📹",
        ToolType.ECHO: "🔊"
    }
    
    # Эмодзи для разных типов операций
    OPERATION_EMOJIS = {
        "create": "➕",
        "update": "✏️",
        "delete": "🗑️",
        "list": "📋",
        "analyze": "🔍",
        "generate": "✨",
        "deploy": "🚀",
        "execute": "⚡"
    }
    
    @classmethod
    def format_confirmation_message(
        cls,
        tool: BaseTool,
        params: BaseToolParams,
        session_id: str,
        expires_at: datetime,
        custom_details: Optional[List[str]] = None
    ) -> str:
        """
        Форматирует сообщение подтверждения
        
        Args:
            tool: Инструмент для выполнения
            params: Параметры инструмента
            session_id: ID сессии подтверждения
            expires_at: Время истечения
            custom_details: Дополнительные детали
            
        Returns:
            Отформатированное сообщение
        """
        metadata = tool.metadata
        tool_type = cls._get_tool_type(tool)
        tool_emoji = cls.TOOL_EMOJIS.get(tool_type, "🔧")
        
        # Заголовок
        message = f"{tool_emoji} **Требуется подтверждение операции**\n\n"
        
        # Информация об инструменте
        message += f"**Инструмент**: {metadata.name}\n"
        message += f"**Описание**: {metadata.description}\n\n"
        
        # Детали операции
        message += "**Детали операции**:\n"
        details = cls._format_operation_details(tool_type, params, custom_details)
        for detail in details:
            message += f"• {detail}\n"
        
        # Параметры (если есть важные)
        important_params = cls._get_important_params(tool_type, params)
        if important_params:
            message += "\n**Параметры**:\n"
            for key, value in important_params.items():
                message += f"• **{cls._humanize_param_name(key)}**: `{value}`\n"
        
        # Предупреждения
        warnings = cls._get_warnings(tool_type, params)
        if warnings:
            message += "\n⚠️ **Внимание**:\n"
            for warning in warnings:
                message += f"• {warning}\n"
        
        # Время и кнопки
        message += f"\n⏱ **Ожидаемое время**: {metadata.estimated_time}\n"
        
        # Время истечения
        time_left = (expires_at - datetime.now()).total_seconds()
        if time_left > 0:
            minutes = int(time_left / 60)
            seconds = int(time_left % 60)
            message += f"⏰ **Истекает через**: {minutes}м {seconds}с\n"
        
        message += "\n**Подтвердить выполнение?**"
        
        return message
    
    @classmethod
    def format_clarification_message(
        cls,
        original_message: str,
        options: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Форматирует сообщение для уточнения намерения
        
        Args:
            original_message: Исходное сообщение пользователя
            options: Варианты для выбора
            metadata: Дополнительные метаданные
            
        Returns:
            Отформатированное сообщение
        """
        message = "🤔 **Уточните, что вы хотите сделать**\n\n"
        
        # Показываем исходное сообщение
        message += f"Ваш запрос: *\"{original_message}\"*\n\n"
        
        # Причина уточнения
        if metadata and metadata.get('reason'):
            message += f"💡 {metadata['reason']}\n\n"
        
        # Варианты
        message += "**Доступные варианты**:\n\n"
        
        for i, option in enumerate(options, 1):
            icon = option.get('icon', '•')
            name = option.get('name', 'Вариант')
            description = option.get('description', '')
            
            message += f"{i}. {icon} **{name}**\n"
            if description:
                message += f"   _{description}_\n"
            message += "\n"
        
        # Инструкция
        message += "Выберите вариант, нажав на соответствующую кнопку."
        
        return message
    
    @classmethod
    def format_success_message(
        cls,
        tool_type: ToolType,
        operation: str,
        result: Optional[Any] = None
    ) -> str:
        """
        Форматирует сообщение об успешном выполнении
        
        Args:
            tool_type: Тип инструмента
            operation: Название операции
            result: Результат выполнения
            
        Returns:
            Отформатированное сообщение
        """
        tool_emoji = cls.TOOL_EMOJIS.get(tool_type, "✅")
        
        message = f"{tool_emoji} **Операция выполнена успешно!**\n\n"
        message += f"**Операция**: {operation}\n"
        
        if result:
            message += "\n**Результат**:\n"
            # Форматируем результат в зависимости от типа
            if isinstance(result, dict):
                for key, value in result.items():
                    if key not in ['metadata', 'raw_response']:
                        message += f"• **{cls._humanize_param_name(key)}**: {value}\n"
            elif isinstance(result, list):
                message += f"Найдено элементов: {len(result)}\n"
            else:
                message += f"{result}\n"
        
        return message
    
    @classmethod
    def format_error_message(
        cls,
        tool_type: ToolType,
        operation: str,
        error: str,
        suggestions: Optional[List[str]] = None
    ) -> str:
        """
        Форматирует сообщение об ошибке
        
        Args:
            tool_type: Тип инструмента
            operation: Название операции
            error: Текст ошибки
            suggestions: Предложения по исправлению
            
        Returns:
            Отформатированное сообщение
        """
        message = "❌ **Ошибка выполнения операции**\n\n"
        message += f"**Операция**: {operation}\n"
        message += f"**Ошибка**: {error}\n"
        
        if suggestions:
            message += "\n💡 **Возможные решения**:\n"
            for suggestion in suggestions:
                message += f"• {suggestion}\n"
        
        return message
    
    @classmethod
    def format_cancelled_message(cls, operation: str) -> str:
        """Форматирует сообщение об отмене операции"""
        return f"🚫 Операция **{operation}** отменена по вашему запросу."
    
    @classmethod
    def format_expired_message(cls, operation: str) -> str:
        """Форматирует сообщение об истечении времени"""
        return f"⏰ Время подтверждения операции **{operation}** истекло."
    
    @classmethod
    def _get_tool_type(cls, tool: BaseTool) -> Optional[ToolType]:
        """Определяет тип инструмента"""
        name = tool.metadata.name
        
        # Мапинг имен на типы
        name_to_type = {
            "mcp_executor": ToolType.MCP,
            "image_generator": ToolType.IMAGE_GENERATOR,
            "vision_analyzer": ToolType.VISION_ANALYZER,
            "echo_tool": ToolType.ECHO
        }
        
        return name_to_type.get(name)
    
    @classmethod
    def _format_operation_details(
        cls,
        tool_type: ToolType,
        params: BaseToolParams,
        custom_details: Optional[List[str]] = None
    ) -> List[str]:
        """Форматирует детали операции в зависимости от типа"""
        details = []
        
        if custom_details:
            return custom_details
        
        # Специфичные детали для каждого типа
        if tool_type == ToolType.MCP:
            if hasattr(params, 'command'):
                details.append(f"Выполнение команды: `{params.command}`")
            details.append("Управление инфраструктурой DigitalOcean")
            details.append("Возможны изменения в приложениях и базах данных")
            
        elif tool_type == ToolType.IMAGE_GENERATOR:
            if hasattr(params, 'prompt'):
                details.append(f"Генерация изображения по описанию")
            if hasattr(params, 'style'):
                details.append(f"Стиль: {params.style}")
            details.append("Использование DALL-E API")
            
        elif tool_type == ToolType.VISION_ANALYZER:
            if hasattr(params, 'url'):
                details.append(f"Анализ контента по ссылке")
            if hasattr(params, 'analysis_type'):
                details.append(f"Тип анализа: {params.analysis_type}")
            details.append("Использование Vision API")
        
        return details
    
    @classmethod
    def _get_important_params(
        cls,
        tool_type: ToolType,
        params: BaseToolParams
    ) -> Dict[str, Any]:
        """Выбирает важные параметры для отображения"""
        params_dict = params.dict()
        important = {}
        
        # Убираем служебные поля
        skip_fields = {'user_id', 'metadata', 'raw_data'}
        
        # Специфичные поля для каждого типа
        if tool_type == ToolType.MCP:
            important_fields = {'command', 'filters', 'app_id', 'database_name'}
        elif tool_type == ToolType.IMAGE_GENERATOR:
            important_fields = {'prompt', 'size', 'quality', 'style'}
        elif tool_type == ToolType.VISION_ANALYZER:
            important_fields = {'url', 'analysis_type', 'frame_interval'}
        else:
            important_fields = set()
        
        for key, value in params_dict.items():
            if key not in skip_fields and (not important_fields or key in important_fields):
                if value is not None:  # Только непустые значения
                    important[key] = value
        
        return important
    
    @classmethod
    def _get_warnings(
        cls,
        tool_type: ToolType,
        params: BaseToolParams
    ) -> List[str]:
        """Генерирует предупреждения для операции"""
        warnings = []
        
        if tool_type == ToolType.MCP:
            warnings.append("Эта операция может изменить состояние вашей инфраструктуры")
            if hasattr(params, 'command') and 'delete' in params.command.lower():
                warnings.append("⚠️ ВНИМАНИЕ: Операция удаления необратима!")
                
        elif tool_type == ToolType.IMAGE_GENERATOR:
            warnings.append("Генерация изображения потребует API credits")
            
        elif tool_type == ToolType.VISION_ANALYZER:
            if hasattr(params, 'url') and 'video' in str(params.url):
                warnings.append("Анализ видео может занять несколько минут")
        
        return warnings
    
    @classmethod
    def _humanize_param_name(cls, param_name: str) -> str:
        """Преобразует название параметра в человекочитаемый вид"""
        # Замены для частых параметров
        replacements = {
            'url': 'URL',
            'prompt': 'Описание',
            'command': 'Команда',
            'size': 'Размер',
            'quality': 'Качество',
            'style': 'Стиль',
            'analysis_type': 'Тип анализа',
            'frame_interval': 'Интервал кадров',
            'app_id': 'ID приложения',
            'database_name': 'База данных'
        }
        
        if param_name in replacements:
            return replacements[param_name]
        
        # Преобразуем snake_case в Title Case
        return param_name.replace('_', ' ').title()