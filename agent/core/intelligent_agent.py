"""
Основной класс Intelligent Agent с поддержкой OpenAI Function Calling
"""
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime

from .models import (
    AgentResponse, ToolResponse, BaseToolParams,
    EchoToolParams, MCPCommandParams, ImageGenerationParams,
    VisionAnalysisParams, ToolType
)

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
                    "name": "analyze_visual_content",
                    "description": "Проанализировать видео или изображение",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL видео или изображения"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "Тип анализа: general, detailed, objects, text, emotions",
                                "default": "general"
                            },
                            "frame_interval": {
                                "type": "integer",
                                "description": "Для видео: каждый N-й кадр",
                                "default": 30
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
            # Подготавливаем сообщения
            messages = self._prepare_messages(message, context)
            
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
                    confidence=0.95,
                    requires_confirmation=False
                )
            else:
                # Обычный ответ без инструментов
                return AgentResponse(
                    message=assistant_message.content or "Не могу сформировать ответ",
                    confidence=0.9,
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
- Для анализа видео/изображений - используй analyze_visual_content
- Для тестирования - используй echo_tool

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
        
        # Выполняем функцию
        if function_name == "echo_tool":
            return await self._execute_echo_tool(EchoToolParams(**function_args))
        elif function_name == "execute_mcp_command":
            return await self._execute_mcp_command(MCPCommandParams(**function_args))
        elif function_name == "generate_image":
            return await self._execute_image_generation(ImageGenerationParams(**function_args))
        elif function_name == "analyze_visual_content":
            return await self._execute_vision_analysis(VisionAnalysisParams(**function_args))
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
        """Заглушка для MCP команд"""
        # TODO: Интегрировать с реальным ClaudeCodeService
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
    
    async def _execute_vision_analysis(self, params: VisionAnalysisParams) -> ToolResponse:
        """Заглушка для анализа видео"""
        # TODO: Интегрировать с GPT-4 Vision
        return ToolResponse(
            success=True,
            data={
                "message": f"Анализ {params.url} будет выполнен",
                "type": params.analysis_type
            },
            metadata={"tool_type": ToolType.VISION_ANALYZER}
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