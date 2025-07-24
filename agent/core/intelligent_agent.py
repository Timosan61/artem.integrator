"""
Основной класс Intelligent Agent с поддержкой OpenAI Function Calling
"""
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from openai import AsyncOpenAI
from datetime import datetime

from .models import (
    AgentResponse, ToolResponse, BaseToolParams,
    EchoToolParams, MCPCommandParams, ImageGenerationParams,
    YouTubeAnalysisParams, ToolType
)
from .intents import Intent
from .preference_manager import preference_manager
from .intent_classifier import IntentClassifier
from .tool_registry import ToolRegistry

if TYPE_CHECKING:
    from ..tools.base import BaseTool

logger = logging.getLogger(__name__)


class IntelligentAgent:
    """Интеллектуальный агент с поддержкой Function Calling"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Инициализация агента
        
        Args:
            api_key: OpenAI API ключ
            model: Модель для использования (по умолчанию gpt-4o)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.conversation_history = []
        
        # Инициализируем компоненты
        self.intent_classifier = IntentClassifier()
        self.tool_registry = ToolRegistry()
        self.preference_manager = preference_manager
        self.logger = logger
        
        # Доступные функции
        self.available_functions = self._get_available_functions()
        
        logger.info(f"✅ IntelligentAgent инициализирован с моделью {model}")
    
    def _get_available_functions(self) -> List[Dict[str, Any]]:
        """Возвращает список доступных функций для OpenAI"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "echo_tool",
                    "description": "Простой инструмент для тестирования, который возвращает эхо сообщения",
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
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_mcp_command",
                    "description": "Выполнить MCP команду для управления инфраструктурой (приложения, базы данных, серверы)",
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
                                "description": "Дополнительные фильтры",
                                "default": {}
                            }
                        },
                        "required": ["command", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Сгенерировать изображение по текстовому описанию",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Детальное описание изображения на английском"
                            },
                            "style": {
                                "type": "string",
                                "description": "Стиль: realistic, cartoon, abstract, oil-painting, watercolor",
                                "default": "realistic"
                            },
                            "size": {
                                "type": "string",
                                "description": "Размер: 1024x1024, 1792x1024, 1024x1792",
                                "default": "1024x1024"
                            },
                            "quality": {
                                "type": "string",
                                "description": "Качество: standard или hd",
                                "default": "standard"
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID пользователя"
                            }
                        },
                        "required": ["prompt", "user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_youtube_video",
                    "description": "Проанализировать YouTube видео, получить субтитры и статистику",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL YouTube видео"
                            },
                            "extract_subtitles": {
                                "type": "boolean",
                                "description": "Извлечь субтитры видео",
                                "default": True
                            },
                            "subtitle_language": {
                                "type": "string",
                                "description": "Язык субтитров (ru, en, auto)",
                                "default": "ru"
                            },
                            "include_metadata": {
                                "type": "boolean",
                                "description": "Включить метаданные видео",
                                "default": True
                            },
                            "user_id": {
                                "type": "string",
                                "description": "ID пользователя"
                            }
                        },
                        "required": ["url", "user_id"]
                    }
                }
            }
        ]
    
    async def process_message(
        self, 
        message: str, 
        user_id: str,
        context: Optional[List[Dict[str, str]]] = None
    ) -> AgentResponse:
        """
        Обрабатывает сообщение пользователя
        
        Args:
            message: Сообщение от пользователя
            user_id: ID пользователя
            context: Контекст предыдущих сообщений
            
        Returns:
            AgentResponse с результатом обработки
        """
        try:
            # Классифицируем намерение
            intent, confidence, metadata = self.intent_classifier.classify(message)
            logger.info(f"🎯 Классифицировано намерение: {intent.value} (confidence: {confidence:.2f})")
            
            # Дополнительное логирование для вопросов об инструментах
            message_lower = message.lower()
            if any(word in message_lower for word in ["инструмент", "tool", "mcp", "умеешь", "можешь"]):
                logger.info(f"📝 Обнаружен вопрос об инструментах/возможностях")
            
            # Проверяем предпочтения пользователя
            available_tools = self._get_available_tool_types(intent)
            preferred_tool = self.preference_manager.get_preferred_tool(
                user_id, intent, available_tools
            )
            
            # Подготавливаем сообщения с учетом предпочтений
            messages = self._prepare_messages_with_preferences(
                message, context, intent, preferred_tool
            )
            
            # Вызываем OpenAI с function calling
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.available_functions,
                tool_choice="auto"
            )
            
            # Получаем ответ
            assistant_message = response.choices[0].message
            
            # Проверяем, нужно ли вызвать функцию
            if assistant_message.tool_calls:
                # Обрабатываем вызовы функций
                tool_response = await self._handle_tool_calls(
                    assistant_message.tool_calls,
                    user_id
                )
                
                # Определяем тип использованного инструмента
                tool_type = self._get_tool_type_from_call(assistant_message.tool_calls[0])
                
                # Записываем выбор для обучения
                if tool_type:
                    self.preference_manager.record_choice(
                        user_id=user_id,
                        message=message,
                        intent=intent,
                        tool_type=tool_type,
                        success=tool_response.success,
                        tool_params=tool_response.data
                    )
                
                # Получаем финальный ответ с результатами функций
                final_response = await self._get_final_response(
                    messages,
                    assistant_message,
                    tool_response
                )
                
                return AgentResponse(
                    message=final_response,
                    tool_used=tool_response.metadata.get("tool_type") if tool_response.metadata else None,
                    tool_response=tool_response,
                    confidence=confidence,
                    requires_confirmation=False,
                    intent=intent
                )
            else:
                # Обычный ответ без инструментов
                return AgentResponse(
                    message=assistant_message.content or "Не могу сформировать ответ",
                    confidence=confidence,
                    requires_confirmation=False,
                    intent=intent
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return AgentResponse(
                message=f"Извините, произошла ошибка: {str(e)}",
                confidence=0.0,
                requires_confirmation=False,
                tool_response=ToolResponse(success=False, error=str(e))
            )
    
    def _prepare_messages(
        self, 
        message: str, 
        context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Подготавливает сообщения для API"""
        system_prompt = """Ты - умный AI ассистент с доступом к различным инструментам.

Анализируй запросы пользователя и используй подходящие инструменты:
- Для вопросов об инфраструктуре (приложения, базы данных, серверы) - используй execute_mcp_command
- Для генерации изображений - используй generate_image
- Для анализа YouTube видео - используй analyze_youtube_video
- Для тестирования - используй echo_tool

ВАЖНО: Когда пользователь спрашивает о доступных инструментах, MCP инструментах или что ты умеешь делать, 
ОБЯЗАТЕЛЬНО используй execute_mcp_command с командой "help" или "list tools" для получения актуального списка возможностей.
НЕ отвечай про инструменты без их вызова!

Отвечай на русском языке, кратко и по существу."""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем контекст если есть
        if context:
            messages.extend(context)
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": message})
        
        return messages
    
    async def _handle_tool_calls(
        self, 
        tool_calls, 
        user_id: str
    ) -> ToolResponse:
        """Обрабатывает вызовы инструментов"""
        # Для простоты обрабатываем только первый вызов
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Добавляем user_id если его нет
        if "user_id" not in function_args:
            function_args["user_id"] = user_id
        
        logger.info(f"🔧 Вызов функции: {function_name} с параметрами: {function_args}")
        
        # Логируем для MCP команд
        if function_name == "execute_mcp_command":
            logger.info(f"🔌 MCP команда обнаружена: {function_args.get('command')}")
        
        # Выполняем функцию
        if function_name == "echo_tool":
            return await self._execute_echo_tool(EchoToolParams(**function_args))
        elif function_name == "execute_mcp_command":
            return await self._execute_mcp_command(MCPCommandParams(**function_args))
        elif function_name == "generate_image":
            return await self._execute_image_generation(ImageGenerationParams(**function_args))
        elif function_name == "analyze_youtube_video":
            return await self._execute_youtube_analysis(YouTubeAnalysisParams(**function_args))
        else:
            return ToolResponse(
                success=False,
                error=f"Неизвестная функция: {function_name}"
            )
    
    async def _execute_echo_tool(self, params: EchoToolParams) -> ToolResponse:
        """Выполняет echo инструмент (для тестирования)"""
        try:
            result = params.message
            if params.uppercase:
                result = result.upper()
            
            return ToolResponse(
                success=True,
                data={"echo": result, "original": params.message},
                metadata={"tool_type": ToolType.ECHO}
            )
        except Exception as e:
            return ToolResponse(success=False, error=str(e))
    
    async def _execute_mcp_command(self, params: MCPCommandParams) -> ToolResponse:
        """Выполняет MCP команду через реальный инструмент"""
        # Получаем MCP tool из реестра
        mcp_tool = self.tool_registry.get_tool("mcp_executor")
        
        if mcp_tool:
            logger.info(f"🔧 Выполнение MCP команды через tool: {params.command}")
            result = await mcp_tool.execute(params)
            return result
        else:
            # Fallback на заглушку
            logger.warning("⚠️ MCP tool не найден в реестре, используем заглушку")
            return ToolResponse(
                success=True,
                data={
                    "message": f"MCP команда '{params.command}' будет выполнена",
                    "command": params.command,
                    "user": params.user_id
                },
                metadata={"tool_type": ToolType.MCP}
            )
    
    async def _execute_image_generation(self, params: ImageGenerationParams) -> ToolResponse:
        """Заглушка для генерации изображений"""
        # TODO: Интегрировать с DALL-E
        return ToolResponse(
            success=True,
            data={
                "message": f"Изображение '{params.prompt}' будет сгенерировано",
                "style": params.style,
                "size": params.size
            },
            metadata={"tool_type": ToolType.IMAGE_GENERATOR}
        )
    
    async def _execute_youtube_analysis(self, params: YouTubeAnalysisParams) -> ToolResponse:
        """Заглушка для анализа YouTube видео"""
        # TODO: Интегрировать с YouTube API
        return ToolResponse(
            success=True,
            data={
                "message": f"Анализ YouTube видео {params.url} будет выполнен",
                "video_url": params.url,
                "extract_subtitles": params.extract_subtitles
            },
            metadata={"tool_type": ToolType.YOUTUBE_ANALYZER}
        )
    
    async def _get_final_response(
        self,
        messages: List[Dict[str, str]],
        assistant_message,
        tool_response: ToolResponse
    ) -> str:
        """Получает финальный ответ после выполнения инструмента"""
        # Добавляем сообщение ассистента с tool_calls
        messages.append({
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": assistant_message.tool_calls
        })
        
        # Добавляем результат выполнения функции
        tool_call = assistant_message.tool_calls[0]
        messages.append({
            "role": "tool",
            "content": json.dumps(tool_response.dict(), ensure_ascii=False),
            "tool_call_id": tool_call.id
        })
        
        # Получаем финальный ответ
        final_response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages
        )
        
        return final_response.choices[0].message.content or "Операция выполнена"
    
    def _get_available_tool_types(self, intent: Intent) -> List[ToolType]:
        """Получает доступные типы инструментов для намерения"""
        # Мапинг намерений на инструменты
        intent_to_tools = {
            Intent.MCP_COMMAND: [ToolType.MCP],
            Intent.IMAGE_GENERATION: [ToolType.IMAGE_GENERATOR],
            Intent.YOUTUBE_ANALYSIS: [ToolType.YOUTUBE_ANALYZER],
            Intent.GENERAL_QUESTION: [ToolType.ECHO],
            Intent.GENERAL_CHAT: [ToolType.ECHO],
            Intent.UNKNOWN: [ToolType.ECHO, ToolType.MCP]
        }
        
        return intent_to_tools.get(intent, [ToolType.ECHO])
    
    def _prepare_messages_with_preferences(
        self,
        message: str,
        context: Optional[List[Dict[str, str]]],
        intent: Intent,
        preferred_tool: Optional[tuple[ToolType, float]]
    ) -> List[Dict[str, str]]:
        """Подготавливает сообщения с учетом предпочтений"""
        system_prompt = """Ты - умный AI ассистент с доступом к различным инструментам.

Анализируй запросы пользователя и используй подходящие инструменты:
- Для вопросов об инфраструктуре (приложения, базы данных, серверы) - используй execute_mcp_command
- Для генерации изображений - используй generate_image
- Для анализа YouTube видео - используй analyze_youtube_video
- Для тестирования - используй echo_tool

Отвечай на русском языке, кратко и по существу."""
        
        # Добавляем информацию о предпочтениях если есть
        if preferred_tool:
            tool_type, confidence = preferred_tool
            tool_hints = {
                ToolType.MCP: "execute_mcp_command",
                ToolType.IMAGE_GENERATOR: "generate_image",
                ToolType.YOUTUBE_ANALYZER: "analyze_youtube_video",
                ToolType.ECHO: "echo_tool"
            }
            
            if tool_type in tool_hints:
                system_prompt += f"\n\nВАЖНО: Пользователь предпочитает использовать {tool_hints[tool_type]} для подобных запросов (уверенность: {confidence:.0%})."
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем контекст если есть
        if context:
            messages.extend(context)
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": message})
        
        return messages
    
    def _get_tool_type_from_call(self, tool_call) -> Optional[ToolType]:
        """Определяет тип инструмента по вызову функции"""
        function_name = tool_call.function.name
        
        # Мапинг имен функций на типы
        function_to_type = {
            "echo_tool": ToolType.ECHO,
            "execute_mcp_command": ToolType.MCP,
            "generate_image": ToolType.IMAGE_GENERATOR,
            "analyze_youtube_video": ToolType.YOUTUBE_ANALYZER
        }
        
        return function_to_type.get(function_name)