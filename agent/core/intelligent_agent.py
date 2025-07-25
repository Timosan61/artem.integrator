"""
Упрощенный Intelligent Agent с прямым LLM-анализом намерений
"""
import json
import logging
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from openai import AsyncOpenAI
from datetime import datetime

from .models import (
    AgentResponse, ToolResponse, BaseToolParams,
    EchoToolParams, ImageGenerationParams,
    YouTubeAnalysisParams, ToolType
)
from .intents import Intent

if TYPE_CHECKING:
    from ..tools.base import BaseTool

logger = logging.getLogger(__name__)


class IntelligentAgent:
    """Упрощенный интеллектуальный агент с прямым LLM-анализом"""
    
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
        
        self.logger = logger
        
        # Импортируем Claude Code Service для прямых вызовов
        self._init_claude_code_service()
        
        # Доступные функции
        self.available_functions = self._get_available_functions()
        
        logger.info(f"✅ Упрощенный IntelligentAgent инициализирован с моделью {model}")
    
    def _init_claude_code_service(self) -> None:
        """Инициализирует Claude Code Service для прямых вызовов"""
        try:
            from bot.services.claude_code_service import claude_code_service
            self.claude_code_service = claude_code_service
            logger.info("✅ Claude Code Service подключен напрямую")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось подключить Claude Code Service: {e}")
            self.claude_code_service = None
    
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
                    "name": "claude_code_direct",
                    "description": "Прямой вызов Claude Code Service для MCP команд и управления инфраструктурой",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "Сообщение пользователя для Claude Code Service (на русском или английском)"
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
        Упрощенная обработка сообщения с прямым LLM-анализом
        
        Args:
            message: Сообщение от пользователя
            user_id: ID пользователя
            context: Контекст предыдущих сообщений
            
        Returns:
            AgentResponse с результатом обработки
        """
        try:
            logger.info(f"🤖 Простая обработка сообщения: '{message[:50]}...' от пользователя {user_id}")
            
            # Упрощенная подготовка сообщений - LLM сам выберет инструмент
            messages = self._prepare_simple_messages(message, context)
            
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
                logger.info(f"🔧 LLM выбрал инструмент: {assistant_message.tool_calls[0].function.name}")
                
                # Обрабатываем вызовы функций
                tool_response = await self._handle_tool_calls(
                    assistant_message.tool_calls,
                    user_id
                )
                
                # Определяем тип использованного инструмента
                tool_type = self._get_tool_type_from_call(assistant_message.tool_calls[0])
                
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
                    confidence=0.9,  # Высокая уверенность - LLM сам выбрал инструмент
                    requires_confirmation=False
                )
            else:
                # Обычный ответ без инструментов
                logger.info("💬 LLM выбрал обычный разговор")
                return AgentResponse(
                    message=assistant_message.content or "Не могу сформировать ответ",
                    confidence=0.8,
                    requires_confirmation=False
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return AgentResponse(
                message=f"Извините, произошла ошибка: {str(e)}",
                confidence=0.0,
                requires_confirmation=False,
                tool_response=ToolResponse(success=False, error=str(e))
            )
    
    def _prepare_simple_messages(
        self, 
        message: str, 
        context: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """Упрощенная подготовка сообщений с прямыми инструкциями для LLM"""
        system_prompt = """Ты - умный AI ассистент Артём Интегратор с доступом к инструментам.

🎯 ТВОЯ ЗАДАЧА: Понять, что хочет пользователь, и выбрать правильный инструмент:

📊 **MCP КОМАНДЫ** (claude_code_direct) - используй для:
- "покажи приложения", "мои приложения", "список приложений"
- "какие у меня MCP сервера", "список серверов", "mcp сервера"
- "какие у меня базы данных", "база данных", "БД"
- "деплойменты", "история деплоев", "развертывания"
- любые вопросы про инфраструктуру DigitalOcean/Supabase

🎥 **YOUTUBE АНАЛИЗ** (analyze_youtube_video) - используй для:
- ссылок на YouTube видео
- "анализ видео", "субтитры", "статистика видео"

🖼️ **ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЙ** (generate_image) - используй для:
- "нарисуй", "создай картинку", "сгенерируй изображение"

💬 **ОБЫЧНЫЙ РАЗГОВОР** - для всего остального:
- приветствия, общие вопросы, помощь

🚀 **КЛЮЧЕВОЕ ПРАВИЛО**: Не думай о паттернах - просто пойми намерение и действуй!

Примеры:
- "какие у меня есть MCP сервера?" → claude_code_direct
- "какие у меня MCP сервера" → claude_code_direct
- "покажи мои приложения" → claude_code_direct
- "список серверов" → claude_code_direct  
- "как дела?" → обычный разговор
- "нарисуй кота" → generate_image

Будь дружелюбным и полезным! 🤖"""
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Добавляем контекст если есть
        if context:
            for ctx_msg in context[-5:]:  # Берем последние 5 сообщений
                messages.append(ctx_msg)
        
        # Добавляем текущее сообщение
        messages.append({"role": "user", "content": message})
        
        return messages
    
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
        
        # Логируем для Claude Code команд
        if function_name == "claude_code_direct":
            logger.info(f"🔌 Claude Code прямой вызов: {function_args.get('message')}")
        
        # Выполняем функцию
        if function_name == "echo_tool":
            return await self._execute_echo_tool(EchoToolParams(**function_args))
        elif function_name == "claude_code_direct":
            return await self._execute_claude_code_direct(function_args)
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
    
    async def _execute_claude_code_direct(self, function_args: Dict[str, Any]) -> ToolResponse:
        """Выполняет прямой вызов Claude Code Service"""
        try:
            message = function_args.get("message")
            user_id = function_args.get("user_id")
            
            logger.info(f"🔌 Прямой вызов Claude Code Service: {message}")
            
            if self.claude_code_service:
                # Прямой вызов Claude Code Service
                result = await self.claude_code_service.execute_mcp_command(message, user_id)
                
                if result.get("success"):
                    return ToolResponse(
                        success=True,
                        data={
                            "message": message,
                            "response": result.get("response", "Команда выполнена"),
                            "mcp_response": result.get("data") or result.get("mcp_response")
                        },
                        metadata={"tool_type": ToolType.MCP}
                    )
                else:
                    return ToolResponse(
                        success=False,
                        error=result.get("error", "Ошибка выполнения Claude Code Service"),
                        metadata={"tool_type": ToolType.MCP}
                    )
            else:
                # Fallback если сервис недоступен
                return ToolResponse(
                    success=False,
                    error="Claude Code Service недоступен",
                    metadata={"tool_type": ToolType.MCP}
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка прямого вызова Claude Code Service: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=f"Ошибка: {str(e)}",
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