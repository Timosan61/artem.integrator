"""
Упрощенный Intelligent Agent с прямым LLM-анализом намерений
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from openai import AsyncOpenAI
import openai
from datetime import datetime
import sys
import os

# Добавляем поддержку Anthropic
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    AsyncAnthropic = None

# Добавляем bot в path для импорта logging_utils
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

try:
    from bot.core.logging_utils import (
        get_structured_logger, ComponentType, TraceContext,
        log_operation_start, log_operation_success, log_operation_error
    )
    STRUCTURED_LOGGING = True
except ImportError:
    STRUCTURED_LOGGING = False

from .models import (
    AgentResponse, ToolResponse, BaseToolParams,
    EchoToolParams, ImageGenerationParams,
    YouTubeAnalysisParams, ToolType
)
from .intents import Intent

if TYPE_CHECKING:
    from ..tools.base import BaseTool

logger = logging.getLogger(__name__)

# Инициализируем структурированный логгер если доступен
if STRUCTURED_LOGGING:
    structured_logger = get_structured_logger("intelligent_agent", ComponentType.AGENT)
else:
    structured_logger = None


class IntelligentAgent:
    """Упрощенный интеллектуальный агент с прямым LLM-анализом и fallback системой"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o", anthropic_api_key: Optional[str] = None):
        """
        Инициализация агента с поддержкой нескольких LLM провайдеров
        
        Args:
            api_key: OpenAI API ключ
            model: Модель для использования (по умолчанию gpt-4o)
            anthropic_api_key: Anthropic API ключ для fallback
        """
        # Инициализация OpenAI клиента (первичный провайдер)
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.openai_model = model
        
        # Инициализация Anthropic клиента (fallback провайдер)
        self.anthropic_client = None
        self.anthropic_model = "claude-3-5-sonnet-20241022"
        
        if anthropic_api_key and ANTHROPIC_AVAILABLE:
            try:
                self.anthropic_client = AsyncAnthropic(api_key=anthropic_api_key)
                logger.info("✅ Anthropic клиент инициализирован для fallback")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка инициализации Anthropic клиента: {e}")
        elif not ANTHROPIC_AVAILABLE:
            logger.warning("⚠️ Anthropic библиотека не доступна")
        
        # Устаревшие свойства для обратной совместимости
        self.client = self.openai_client
        self.model = self.openai_model
        self.conversation_history = []
        
        self.logger = logger
        self.structured_logger = structured_logger if STRUCTURED_LOGGING else None
        
        # Импортируем Claude Code Service для прямых вызовов
        self._init_claude_code_service()
        
        # Доступные функции
        self.available_functions = self._get_available_functions()
        
        # Статистика использования провайдеров
        self.provider_stats = {
            "openai_calls": 0,
            "anthropic_calls": 0,
            "claude_sdk_calls": 0,
            "openai_errors": 0,
            "anthropic_errors": 0
        }
        
        providers_available = []
        if api_key:
            providers_available.append("OpenAI")
        if self.anthropic_client:
            providers_available.append("Anthropic")
        if hasattr(self, 'claude_code_service') and self.claude_code_service:
            providers_available.append("Claude SDK")
            
        logger.info(f"✅ IntelligentAgent инициализирован с провайдерами: {', '.join(providers_available)}")
    
    def _init_claude_code_service(self) -> None:
        """Инициализирует Claude Code Service для прямых вызовов"""
        try:
            from bot.services.claude_code_service import claude_code_service
            self.claude_code_service = claude_code_service
            logger.info("✅ Claude Code Service подключен напрямую")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось подключить Claude Code Service: {e}")
            self.claude_code_service = None
    
    async def _call_llm_with_fallback(
        self, 
        messages: List[Dict[str, str]], 
        trace_id: str = "no-trace"
    ) -> Dict[str, Any]:
        """
        Универсальный метод для вызова LLM с автоматическим fallback
        
        Args:
            messages: Сообщения для LLM
            trace_id: ID трассировки для логирования
            
        Returns:
            Ответ от LLM в стандартном формате
        """
        
        # Попытка 1: OpenAI
        try:
            self.structured_logger.info(
                f"🧠 Попытка 1: Вызов OpenAI ({self.openai_model})",
                trace_id=trace_id,
                operation="openai_request",
                metadata={"model": self.openai_model, "provider": "openai"}
            )
            
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                tools=self.available_functions,
                tool_choice="auto"
            )
            
            self.provider_stats["openai_calls"] += 1
            
            self.structured_logger.info(
                "✅ OpenAI ответ получен успешно",
                trace_id=trace_id,
                operation="openai_success",
                metadata={"provider": "openai", "model": self.openai_model}
            )
            
            # Возвращаем в стандартном формате
            return {
                "provider": "openai",
                "model": self.openai_model,
                "message": response.choices[0].message,
                "success": True
            }
            
        except openai.RateLimitError as e:
            self.provider_stats["openai_errors"] += 1
            self.structured_logger.warning(
                f"⚠️ OpenAI квота превышена (429), переключаемся на Anthropic",
                trace_id=trace_id,
                operation="openai_rate_limit",
                metadata={"error": str(e), "provider": "openai"}
            )
            
        except openai.AuthenticationError as e:
            self.provider_stats["openai_errors"] += 1
            self.structured_logger.error(
                f"❌ OpenAI аутентификация неуспешна (401), переключаемся на Anthropic",
                trace_id=trace_id,
                operation="openai_auth_error",
                metadata={"error": str(e), "provider": "openai"}
            )
            
        except openai.APIError as e:
            self.provider_stats["openai_errors"] += 1
            self.structured_logger.error(
                f"❌ OpenAI API ошибка ({e.status_code}), переключаемся на Anthropic",
                trace_id=trace_id,
                operation="openai_api_error",
                metadata={"error": str(e), "status_code": getattr(e, 'status_code', None), "provider": "openai"}
            )
            
        except Exception as e:
            self.provider_stats["openai_errors"] += 1
            self.structured_logger.error(
                f"❌ OpenAI неожиданная ошибка, переключаемся на Anthropic",
                trace_id=trace_id,
                operation="openai_unexpected_error",
                metadata={"error": str(e), "provider": "openai"}
            )
        
        # Попытка 2: Anthropic
        if self.anthropic_client:
            try:
                self.structured_logger.info(
                    f"🤖 Попытка 2: Вызов Anthropic ({self.anthropic_model})",
                    trace_id=trace_id,
                    operation="anthropic_request",
                    metadata={"model": self.anthropic_model, "provider": "anthropic"}
                )
                
                # Конвертируем OpenAI формат в Anthropic формат
                anthropic_messages = self._convert_messages_for_anthropic(messages)
                
                response = await self.anthropic_client.messages.create(
                    model=self.anthropic_model,
                    max_tokens=4096,
                    messages=anthropic_messages
                )
                
                self.provider_stats["anthropic_calls"] += 1
                
                self.structured_logger.info(
                    "✅ Anthropic ответ получен успешно",
                    trace_id=trace_id,
                    operation="anthropic_success",
                    metadata={"provider": "anthropic", "model": self.anthropic_model}
                )
                
                # Конвертируем Anthropic ответ в OpenAI формат для совместимости
                return {
                    "provider": "anthropic",
                    "model": self.anthropic_model,
                    "message": self._convert_anthropic_response_to_openai(response),
                    "success": True
                }
                
            except Exception as e:
                self.provider_stats["anthropic_errors"] += 1
                self.structured_logger.error(
                    f"❌ Anthropic ошибка, переключаемся на Claude SDK",
                    trace_id=trace_id,
                    operation="anthropic_error", 
                    metadata={"error": str(e), "provider": "anthropic"}
                )
        else:
            self.structured_logger.warning(
                "⚠️ Anthropic клиент недоступен, переключаемся на Claude SDK",
                trace_id=trace_id,
                operation="anthropic_unavailable"
            )
        
        # Попытка 3: Claude Code SDK
        if self.claude_code_service:
            try:
                self.structured_logger.info(
                    "🔌 Попытка 3: Вызов Claude Code SDK",
                    trace_id=trace_id,
                    operation="claude_sdk_request",
                    metadata={"provider": "claude_sdk"}
                )
                
                # Извлекаем последнее пользовательское сообщение
                user_message = None
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break
                
                if user_message:
                    sdk_response = await self.claude_code_service.execute_mcp_command(
                        user_message, 
                        user_id="fallback",
                        trace_id=trace_id
                    )
                    
                    self.provider_stats["claude_sdk_calls"] += 1
                    
                    if sdk_response.get("success"):
                        self.structured_logger.info(
                            "✅ Claude SDK ответ получен успешно",
                            trace_id=trace_id,
                            operation="claude_sdk_success",
                            metadata={"provider": "claude_sdk"}
                        )
                        
                        # Эмулируем OpenAI формат ответа
                        mock_message = type('MockMessage', (), {
                            'content': sdk_response.get("response", "Ответ получен от Claude SDK"),
                            'tool_calls': None
                        })()
                        
                        return {
                            "provider": "claude_sdk",
                            "model": "claude-code-sdk",
                            "message": mock_message,
                            "success": True
                        }
                        
            except Exception as e:
                self.structured_logger.error(
                    f"❌ Claude SDK ошибка",
                    trace_id=trace_id,
                    operation="claude_sdk_error",
                    metadata={"error": str(e), "provider": "claude_sdk"}
                )
        else:
            self.structured_logger.warning(
                "⚠️ Claude SDK недоступен",
                trace_id=trace_id,
                operation="claude_sdk_unavailable"
            )
        
        # Все провайдеры недоступны
        self.structured_logger.error(
            "🚨 ВСЕ LLM провайдеры недоступны!",
            trace_id=trace_id,
            operation="all_providers_failed"
        )
        
        raise Exception("Все LLM провайдеры недоступны. Попробуйте позже.")
    
    def _convert_messages_for_anthropic(self, openai_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Конвертирует OpenAI формат сообщений в формат Anthropic"""
        anthropic_messages = []
        
        for msg in openai_messages:
            if msg["role"] == "system":
                # Anthropic не поддерживает системные сообщения в messages, добавляем как user
                anthropic_messages.append({
                    "role": "user",
                    "content": f"[SYSTEM] {msg['content']}"
                })
            elif msg["role"] in ["user", "assistant"]:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
                
        return anthropic_messages
    
    def _convert_anthropic_response_to_openai(self, anthropic_response) -> object:
        """Конвертирует ответ Anthropic в формат OpenAI для совместимости"""
        
        # Создаем mock объект в стиле OpenAI ответа
        mock_message = type('MockMessage', (), {
            'content': anthropic_response.content[0].text if anthropic_response.content else "Нет ответа",
            'tool_calls': None  # Пока не поддерживаем tools для Anthropic
        })()
        
        return mock_message
    
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
        import uuid
        import time
        
        # Используем структурированное логирование если доступно
        if self.structured_logger:
            trace_id = str(uuid.uuid4())[:8]
            
            with TraceContext(trace_id=trace_id, user_id=user_id, operation="process_message") as trace:
                start_time = time.time()
                
                log_operation_start(
                    self.structured_logger,
                    "process_message",
                    trace_id=trace_id,
                    message_length=len(message),
                    context_messages=len(context) if context else 0,
                    user_id=user_id
                )
                
                self.structured_logger.info(
                    f"🚀 IntelligentAgent начинает обработку сообщения",
                    trace_id=trace_id,
                    operation="process_message",
                    metadata={
                        "message_preview": message[:100] + ('...' if len(message) > 100 else ''),
                        "message_length": len(message),
                        "context_messages": len(context) if context else 0
                    }
                )
                
                try:
                    return await self._process_with_structured_logging(message, user_id, context, trace_id, start_time)
                except Exception as e:
                    duration = time.time() - start_time
                    log_operation_error(
                        self.structured_logger,
                        "process_message", 
                        e,
                        trace_id=trace_id,
                        duration=duration
                    )
                    raise
        else:
            # Fallback к обычному логированию
            trace_id = str(uuid.uuid4())[:8]
            
            try:
                logger.info(f"🚀 [TRACE:{trace_id}] IntelligentAgent начинает обработку сообщения")
                logger.info(f"📝 [TRACE:{trace_id}] Сообщение: '{message[:100]}{'...' if len(message) > 100 else ''}'")
                logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {user_id}")
                logger.info(f"📚 [TRACE:{trace_id}] Контекст: {len(context) if context else 0} сообщений")
            
                return await self._process_with_legacy_logging(message, user_id, context, trace_id)
            except Exception as e:
                logger.error(f"❌ [TRACE:{trace_id}] Критическая ошибка обработки сообщения: {e}", exc_info=True)
                return AgentResponse(
                    message=f"Извините, произошла ошибка: {str(e)}",
                    confidence=0.0,
                    requires_confirmation=False,
                    tool_response=ToolResponse(success=False, error=str(e))
                )
    
    async def _process_with_structured_logging(
        self, 
        message: str, 
        user_id: str, 
        context: Optional[List[Dict[str, str]]], 
        trace_id: str,
        start_time: float
    ) -> AgentResponse:
        """Обработка сообщения с использованием структурированного логирования"""
        try:
            # 1. АНАЛИЗ СООБЩЕНИЯ
            self.structured_logger.info(
                "🔍 Этап 1: Анализ намерения пользователя",
                trace_id=trace_id,
                operation="intent_analysis"
            )
            
            intent_analysis = self._analyze_user_intent(message)
            
            self.structured_logger.info(
                "🎯 Определено намерение пользователя",
                trace_id=trace_id,
                operation="intent_analysis",
                metadata={"intent": intent_analysis}
            )
            
            # 2. ПОДГОТОВКА КОНТЕКСТА
            self.structured_logger.info(
                "⚙️ Этап 2: Подготовка контекста для LLM",
                trace_id=trace_id,
                operation="prepare_context"
            )
            
            messages = self._prepare_simple_messages(message, context)
            
            self.structured_logger.info(
                "📋 Контекст для LLM подготовлен",
                trace_id=trace_id,
                operation="prepare_context",
                metadata={
                    "messages_count": len(messages),
                    "system_prompt_preview": messages[0]['content'][:200] + "..."
                }
            )
            
            # 3. ВЫЗОВ LLM С FALLBACK
            self.structured_logger.info(
                f"🧠 Этап 3: Отправка запроса к LLM с fallback системой",
                trace_id=trace_id,
                operation="llm_request",
                metadata={
                    "available_tools": [func['function']['name'] for func in self.available_functions],
                    "tools_count": len(self.available_functions)
                }
            )
            
            # Используем универсальный метод с fallback логикой
            llm_response = await self._call_llm_with_fallback(messages, trace_id)
            
            # Получаем ответ и информацию о провайдере
            assistant_message = llm_response["message"]
            used_provider = llm_response["provider"]
            used_model = llm_response["model"]
            
            self.structured_logger.info(
                f"💭 LLM ответ получен от {used_provider} ({used_model})",
                trace_id=trace_id,
                operation="llm_response",
                metadata={
                    "provider": used_provider,
                    "model": used_model,
                    "has_tool_calls": bool(assistant_message.tool_calls),
                    "tool_calls_count": len(assistant_message.tool_calls) if assistant_message.tool_calls else 0,
                    "content_length": len(assistant_message.content or "")
                }
            )
            
            # 4. АНАЛИЗ РЕШЕНИЯ LLM
            if assistant_message.tool_calls:
                selected_tool = assistant_message.tool_calls[0].function.name
                tool_args = assistant_message.tool_calls[0].function.arguments
                
                self.structured_logger.info(
                    "🎯 Этап 4: LLM принял решение использовать инструмент",
                    trace_id=trace_id,
                    operation="tool_selection",
                    metadata={
                        "selected_tool": selected_tool,
                        "tool_arguments": tool_args,
                        "decision_confidence": "high"
                    }
                )
                
                # Анализируем логику выбора
                self._log_tool_selection_reasoning_structured(trace_id, message, selected_tool, intent_analysis)
                
                # 5. ВЫПОЛНЕНИЕ ИНСТРУМЕНТА
                self.structured_logger.info(
                    "⚡ Этап 5: Выполнение выбранного инструмента",
                    trace_id=trace_id,
                    operation="tool_execution",
                    metadata={"tool_name": selected_tool}
                )
                tool_response = await self._handle_tool_calls(
                    assistant_message.tool_calls,
                    user_id,
                    trace_id
                )
                
                # Определяем тип использованного инструмента
                tool_type = self._get_tool_type_from_call(assistant_message.tool_calls[0])
                
                self.structured_logger.info(
                    "🏷️ Тип инструмента определен",
                    trace_id=trace_id,
                    operation="tool_type_detection",
                    metadata={"tool_type": tool_type}
                )
                
                # 6. ФИНАЛЬНАЯ ГЕНЕРАЦИЯ ОТВЕТА
                self.structured_logger.info(
                    "📝 Этап 6: Генерация финального ответа",
                    trace_id=trace_id,
                    operation="final_response_generation"
                )
                final_response = await self._get_final_response(
                    messages,
                    assistant_message,
                    tool_response,
                    trace_id
                )
                
                duration = time.time() - start_time
                
                log_operation_success(
                    self.structured_logger,
                    "process_message",
                    trace_id=trace_id,
                    duration=duration,
                    tool_used=selected_tool,
                    response_length=len(final_response),
                    confidence=0.9
                )
                
                self.structured_logger.info(
                    "✅ Обработка завершена успешно с инструментом",
                    trace_id=trace_id,
                    operation="completion",
                    metadata={
                        "success": True,
                        "tool_used": selected_tool,
                        "response_length": len(final_response),
                        "duration_seconds": duration,
                        "confidence": 0.9
                    }
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
                self.structured_logger.info(
                    "💬 Этап 4: LLM принял решение об обычном разговоре",
                    trace_id=trace_id,
                    operation="conversation_response",
                    metadata={"reason": "no_tools_required"}
                )
                
                response_text = assistant_message.content or "Не могу сформировать ответ"
                duration = time.time() - start_time
                
                log_operation_success(
                    self.structured_logger,
                    "process_message",
                    trace_id=trace_id,
                    duration=duration,
                    response_length=len(response_text),
                    confidence=0.8
                )
                
                self.structured_logger.info(
                    "✅ Обработка завершена без инструментов",
                    trace_id=trace_id,
                    operation="completion",
                    metadata={
                        "success": True,
                        "tool_used": None,
                        "response_length": len(response_text),
                        "duration_seconds": duration,
                        "confidence": 0.8
                    }
                )
                
                return AgentResponse(
                    message=response_text,
                    confidence=0.8,
                    requires_confirmation=False
                )
                
        except Exception as e:
            duration = time.time() - start_time
            log_operation_error(
                self.structured_logger,
                "process_message",
                e,
                trace_id=trace_id,
                duration=duration
            )
            
            self.structured_logger.error(
                "🚨 Критическая ошибка - возвращаем ошибку пользователю",
                trace_id=trace_id,
                operation="error_handling",
                exc_info=True
            )
            
            return AgentResponse(
                message=f"Извините, произошла ошибка: {str(e)}",
                confidence=0.0,
                requires_confirmation=False,
                tool_response=ToolResponse(success=False, error=str(e))
            )
    
    async def _process_with_legacy_logging(
        self, 
        message: str, 
        user_id: str, 
        context: Optional[List[Dict[str, str]]], 
        trace_id: str
    ) -> AgentResponse:
        """Обработка сообщения с использованием обычного логирования (fallback)"""
        # 1. АНАЛИЗ СООБЩЕНИЯ
        logger.info(f"🔍 [TRACE:{trace_id}] Этап 1: Анализ намерения пользователя...")
        intent_analysis = self._analyze_user_intent(message)
        logger.info(f"🎯 [TRACE:{trace_id}] Определено намерение: {intent_analysis}")
        
        # 2. ПОДГОТОВКА КОНТЕКСТА
        logger.info(f"⚙️ [TRACE:{trace_id}] Этап 2: Подготовка контекста для LLM...")
        messages = self._prepare_simple_messages(message, context)
        logger.info(f"📋 [TRACE:{trace_id}] Подготовлено {len(messages)} сообщений для LLM")
        logger.debug(f"📋 [TRACE:{trace_id}] System prompt: {messages[0]['content'][:200]}...")
        
        # 3. ВЫЗОВ LLM С FALLBACK
        logger.info(f"🧠 [TRACE:{trace_id}] Этап 3: Отправка запроса к LLM с fallback системой...")
        logger.info(f"🛠️ [TRACE:{trace_id}] Доступные инструменты: {len(self.available_functions)}")
        for func in self.available_functions:
            logger.debug(f"🔧 [TRACE:{trace_id}] - {func['function']['name']}: {func['function']['description']}")
        
        # Используем универсальный метод с fallback логикой
        try:
            llm_response = await self._call_llm_with_fallback(messages, trace_id)
            # Получаем ответ и информацию о провайдере
            assistant_message = llm_response["message"]
            used_provider = llm_response["provider"]
            used_model = llm_response["model"]
            logger.info(f"💭 [TRACE:{trace_id}] LLM ответ получен от {used_provider} ({used_model})")
        except Exception as e:
            logger.error(f"❌ [TRACE:{trace_id}] Все LLM провайдеры недоступны: {e}")
            return AgentResponse(
                message=f"Извините, сервис временно недоступен: {str(e)}",
                confidence=0.0,
                requires_confirmation=False,
                tool_response=ToolResponse(success=False, error=str(e))
            )
        
        # 4. АНАЛИЗ РЕШЕНИЯ LLM
        if assistant_message.tool_calls:
            selected_tool = assistant_message.tool_calls[0].function.name
            tool_args = assistant_message.tool_calls[0].function.arguments
            
            logger.info(f"🎯 [TRACE:{trace_id}] Этап 4: LLM принял решение использовать инструмент")
            logger.info(f"🔧 [TRACE:{trace_id}] Выбранный инструмент: {selected_tool}")
            logger.info(f"📋 [TRACE:{trace_id}] Аргументы инструмента: {tool_args}")
            
            # Анализируем логику выбора
            self._log_tool_selection_reasoning(trace_id, message, selected_tool, intent_analysis)
            
            # 5. ВЫПОЛНЕНИЕ ИНСТРУМЕНТА
            logger.info(f"⚡ [TRACE:{trace_id}] Этап 5: Выполнение выбранного инструмента...")
            tool_response = await self._handle_tool_calls(
                assistant_message.tool_calls,
                user_id,
                trace_id
            )
            
            # Определяем тип использованного инструмента
            tool_type = self._get_tool_type_from_call(assistant_message.tool_calls[0])
            logger.info(f"🏷️ [TRACE:{trace_id}] Тип инструмента: {tool_type}")
            
            # 6. ФИНАЛЬНАЯ ГЕНЕРАЦИЯ ОТВЕТА
            logger.info(f"📝 [TRACE:{trace_id}] Этап 6: Генерация финального ответа...")
            final_response = await self._get_final_response(
                messages,
                assistant_message,
                tool_response,
                trace_id
            )
            
            logger.info(f"✅ [TRACE:{trace_id}] Обработка завершена успешно с инструментом {selected_tool}")
            logger.info(f"📊 [TRACE:{trace_id}] Результат: {len(final_response)} символов")
            
            return AgentResponse(
                message=final_response,
                tool_used=tool_response.metadata.get("tool_type") if tool_response.metadata else None,
                tool_response=tool_response,
                confidence=0.9,  # Высокая уверенность - LLM сам выбрал инструмент
                requires_confirmation=False
            )
        else:
            # Обычный ответ без инструментов
            logger.info(f"💬 [TRACE:{trace_id}] Этап 4: LLM принял решение об обычном разговоре")
            logger.info(f"📝 [TRACE:{trace_id}] Причина: не требуется использование инструментов")
            logger.info(f"✅ [TRACE:{trace_id}] Обработка завершена без инструментов")
            
            response_text = assistant_message.content or "Не могу сформировать ответ"
            logger.info(f"📊 [TRACE:{trace_id}] Результат: {len(response_text)} символов")
            
            return AgentResponse(
                message=response_text,
                confidence=0.8,
                requires_confirmation=False
            )
    
    def _log_tool_selection_reasoning_structured(
        self, 
        trace_id: str, 
        message: str, 
        selected_tool: str, 
        intent_analysis: str
    ):
        """Структурированное логирование логики выбора инструмента"""
        self.structured_logger.info(
            "🧠 Анализ логики выбора инструмента LLM",
            trace_id=trace_id,
            operation="tool_selection_reasoning",
            metadata={
                "message_preview": message[:100],
                "selected_tool": selected_tool,
                "intent_analysis": intent_analysis,
                "reasoning_factors": {
                    "message_keywords": self._extract_keywords(message),
                    "tool_match_confidence": self._assess_tool_match_confidence(message, selected_tool)
                }
            }
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
    
    def _analyze_user_intent(self, message: str) -> str:
        """Анализирует намерение пользователя для логирования"""
        message_lower = message.lower()
        
        # MCP команды
        mcp_keywords = ['мои приложения', 'список приложений', 'mcp сервера', 'какие у меня', 'покажи', 'базы данных', 'деплой']
        if any(keyword in message_lower for keyword in mcp_keywords):
            return "MCP_COMMAND (инфраструктура/сервера)"
            
        # YouTube анализ
        if 'youtube.com' in message_lower or 'youtu.be' in message_lower or 'видео' in message_lower:
            return "YOUTUBE_ANALYSIS (анализ видео)"
            
        # Генерация изображений
        image_keywords = ['нарисуй', 'создай картинку', 'сгенерируй изображение', 'изображение']
        if any(keyword in message_lower for keyword in image_keywords):
            return "IMAGE_GENERATION (создание изображения)"
            
        # Обычный разговор
        return "GENERAL_CHAT (обычное общение)"
    
    def _log_tool_selection_reasoning(self, trace_id: str, message: str, selected_tool: str, intent_analysis: str):
        """Логирует логику выбора инструмента"""
        logger.info(f"🤔 [TRACE:{trace_id}] АНАЛИЗ ВЫБОРА ИНСТРУМЕНТА:")
        logger.info(f"   📝 Исходное сообщение: '{message[:100]}...'")
        logger.info(f"   🎯 Определенное намерение: {intent_analysis}")
        logger.info(f"   🔧 Выбранный LLM инструмент: {selected_tool}")
        
        # Анализ соответствия
        intent_tool_mapping = {
            "MCP_COMMAND": "claude_code_direct",
            "YOUTUBE_ANALYSIS": "analyze_youtube_video", 
            "IMAGE_GENERATION": "generate_image",
            "GENERAL_CHAT": "echo_tool или разговор"
        }
        
        expected_tool = None
        for intent_key, tool_name in intent_tool_mapping.items():
            if intent_key in intent_analysis:
                expected_tool = tool_name
                break
                
        if expected_tool and selected_tool in expected_tool:
            logger.info(f"   ✅ Выбор корректен: {selected_tool} соответствует намерению")
        elif expected_tool:
            logger.warning(f"   ⚠️ Неожиданный выбор: ожидался {expected_tool}, выбран {selected_tool}")
        else:
            logger.info(f"   🔄 Анализ выбора: LLM принял решение на основе контекста")

    async def _handle_tool_calls(
        self, 
        tool_calls, 
        user_id: str,
        trace_id: str = None
    ) -> ToolResponse:
        """Обрабатывает вызовы инструментов"""
        if not trace_id:
            trace_id = "no-trace"
            
        # Для простоты обрабатываем только первый вызов
        tool_call = tool_calls[0]
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        logger.info(f"🔧 [TRACE:{trace_id}] Начинаем выполнение инструмента: {function_name}")
        logger.info(f"📋 [TRACE:{trace_id}] Исходные аргументы: {function_args}")
        
        # Добавляем user_id если его нет
        if "user_id" not in function_args:
            function_args["user_id"] = user_id
            logger.debug(f"➕ [TRACE:{trace_id}] Добавлен user_id: {user_id}")
        
        logger.info(f"⚙️ [TRACE:{trace_id}] Финальные параметры: {function_args}")
        
        # Специальное логирование для разных типов инструментов
        if function_name == "claude_code_direct":
            logger.info(f"🔌 [TRACE:{trace_id}] CLAUDE CODE ВЫЗОВ:")
            logger.info(f"   📝 Сообщение для Claude Code: '{function_args.get('message')}'")
            logger.info(f"   👤 Пользователь: {function_args.get('user_id')}")
            logger.info(f"   🎯 Ожидается: MCP команда или инфраструктурный запрос")
        elif function_name == "generate_image":
            logger.info(f"🖼️ [TRACE:{trace_id}] ГЕНЕРАЦИЯ ИЗОБРАЖЕНИЯ:")
            logger.info(f"   📝 Промпт: '{function_args.get('prompt')}'")
            logger.info(f"   🎨 Стиль: {function_args.get('style', 'realistic')}")
            logger.info(f"   📏 Размер: {function_args.get('size', '1024x1024')}")
        elif function_name == "analyze_youtube_video":
            logger.info(f"🎥 [TRACE:{trace_id}] АНАЛИЗ YOUTUBE:")
            logger.info(f"   🔗 URL: {function_args.get('url')}")
            logger.info(f"   📝 Субтитры: {function_args.get('extract_subtitles', True)}")
            logger.info(f"   🌐 Язык: {function_args.get('subtitle_language', 'ru')}")
        elif function_name == "echo_tool":
            logger.info(f"🔄 [TRACE:{trace_id}] ECHO ИНСТРУМЕНТ:")
            logger.info(f"   📝 Сообщение: '{function_args.get('message')}'")
            logger.info(f"   🔠 Верхний регистр: {function_args.get('uppercase', False)}")
        
        # Выполняем функцию с измерением времени
        import time
        start_time = time.time()
        
        try:
            logger.info(f"⚡ [TRACE:{trace_id}] Запуск выполнения инструмента...")
            
            if function_name == "echo_tool":
                result = await self._execute_echo_tool(EchoToolParams(**function_args), trace_id)
            elif function_name == "claude_code_direct":
                result = await self._execute_claude_code_direct(function_args, trace_id)
            elif function_name == "generate_image":
                result = await self._execute_image_generation(ImageGenerationParams(**function_args), trace_id)
            elif function_name == "analyze_youtube_video":
                result = await self._execute_youtube_analysis(YouTubeAnalysisParams(**function_args), trace_id)
            else:
                logger.error(f"❌ [TRACE:{trace_id}] Неизвестная функция: {function_name}")
                return ToolResponse(
                    success=False,
                    error=f"Неизвестная функция: {function_name}"
                )
                
            execution_time = time.time() - start_time
            logger.info(f"✅ [TRACE:{trace_id}] Инструмент выполнен за {execution_time:.2f}с")
            logger.info(f"📊 [TRACE:{trace_id}] Результат: success={result.success}")
            
            if result.success:
                logger.info(f"✨ [TRACE:{trace_id}] Данные получены: {len(str(result.data))} символов")
            else:
                logger.warning(f"⚠️ [TRACE:{trace_id}] Ошибка выполнения: {result.error}")
                
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"💥 [TRACE:{trace_id}] Критическая ошибка выполнения инструмента за {execution_time:.2f}с: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=f"Ошибка выполнения {function_name}: {str(e)}"
            )
    
    async def _execute_echo_tool(self, params: EchoToolParams, trace_id: str = None) -> ToolResponse:
        """Выполняет echo инструмент (для тестирования)"""
        if not trace_id:
            trace_id = "no-trace"
            
        try:
            logger.info(f"🔄 [TRACE:{trace_id}] Echo инструмент: обработка сообщения")
            
            result = params.message
            if params.uppercase:
                result = result.upper()
                logger.info(f"🔠 [TRACE:{trace_id}] Применен верхний регистр")
            
            logger.info(f"✅ [TRACE:{trace_id}] Echo завершен успешно")
            
            return ToolResponse(
                success=True,
                data={"echo": result, "original": params.message},
                metadata={"tool_type": ToolType.ECHO}
            )
        except Exception as e:
            logger.error(f"❌ [TRACE:{trace_id}] Ошибка Echo инструмента: {e}")
            return ToolResponse(success=False, error=str(e))
    
    async def _execute_claude_code_direct(self, function_args: Dict[str, Any], trace_id: str = None) -> ToolResponse:
        """Выполняет прямой вызов Claude Code Service"""
        if not trace_id:
            trace_id = "no-trace"
            
        try:
            message = function_args.get("message")
            user_id = function_args.get("user_id")
            
            logger.info(f"🔌 [TRACE:{trace_id}] Начинаем прямой вызов Claude Code Service")
            logger.info(f"📝 [TRACE:{trace_id}] Команда: '{message}'")
            logger.info(f"👤 [TRACE:{trace_id}] Пользователь: {user_id}")
            
            if self.claude_code_service:
                logger.info(f"✅ [TRACE:{trace_id}] Claude Code Service доступен, выполняем вызов...")
                
                # Прямой вызов Claude Code Service с передачей trace_id
                result = await self.claude_code_service.execute_mcp_command(message, user_id, trace_id)
                
                logger.info(f"📊 [TRACE:{trace_id}] Получен результат от Claude Code Service")
                logger.info(f"🎯 [TRACE:{trace_id}] Success: {result.get('success')}")
                
                if result.get("success"):
                    response_text = result.get("response", "Команда выполнена")
                    mcp_data = result.get("data") or result.get("mcp_response")
                    
                    logger.info(f"✅ [TRACE:{trace_id}] Claude Code успешно выполнен")
                    logger.info(f"📝 [TRACE:{trace_id}] Ответ: {len(response_text)} символов")
                    logger.info(f"📦 [TRACE:{trace_id}] MCP данные: {len(str(mcp_data)) if mcp_data else 0} символов")
                    
                    return ToolResponse(
                        success=True,
                        data={
                            "message": message,
                            "response": response_text,
                            "mcp_response": mcp_data
                        },
                        metadata={"tool_type": ToolType.MCP}
                    )
                else:
                    error_msg = result.get("error", "Ошибка выполнения Claude Code Service")
                    logger.warning(f"⚠️ [TRACE:{trace_id}] Claude Code вернул ошибку: {error_msg}")
                    
                    return ToolResponse(
                        success=False,
                        error=error_msg,
                        metadata={"tool_type": ToolType.MCP}
                    )
            else:
                logger.error(f"❌ [TRACE:{trace_id}] Claude Code Service недоступен")
                
                # Fallback если сервис недоступен
                return ToolResponse(
                    success=False,
                    error="Claude Code Service недоступен",
                    metadata={"tool_type": ToolType.MCP}
                )
                
        except Exception as e:
            logger.error(f"💥 [TRACE:{trace_id}] Критическая ошибка Claude Code Service: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=f"Ошибка: {str(e)}",
                metadata={"tool_type": ToolType.MCP}
            )
    
    async def _execute_image_generation(self, params: ImageGenerationParams, trace_id: str = None) -> ToolResponse:
        """Заглушка для генерации изображений"""
        if not trace_id:
            trace_id = "no-trace"
            
        logger.info(f"🖼️ [TRACE:{trace_id}] Генерация изображения (заглушка)")
        logger.info(f"📝 [TRACE:{trace_id}] Промпт: '{params.prompt}'")
        logger.info(f"🎨 [TRACE:{trace_id}] Стиль: {params.style}, Размер: {params.size}")
        
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
    
    async def _execute_youtube_analysis(self, params: YouTubeAnalysisParams, trace_id: str = None) -> ToolResponse:
        """Заглушка для анализа YouTube видео"""
        if not trace_id:
            trace_id = "no-trace"
            
        logger.info(f"🎥 [TRACE:{trace_id}] Анализ YouTube видео (заглушка)")
        logger.info(f"🔗 [TRACE:{trace_id}] URL: {params.url}")
        logger.info(f"📝 [TRACE:{trace_id}] Субтитры: {params.extract_subtitles}, Язык: {params.subtitle_language}")
        
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
        tool_response: ToolResponse,
        trace_id: str = None
    ) -> str:
        """Получает финальный ответ после выполнения инструмента"""
        if not trace_id:
            trace_id = "no-trace"
            
        logger.info(f"📝 [TRACE:{trace_id}] Подготовка контекста для генерации финального ответа")
        
        # Добавляем сообщение ассистента с tool_calls
        messages.append({
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": assistant_message.tool_calls
        })
        
        # Добавляем результат выполнения функции
        tool_call = assistant_message.tool_calls[0]
        tool_result_content = json.dumps(tool_response.dict(), ensure_ascii=False)
        
        messages.append({
            "role": "tool",
            "content": tool_result_content,
            "tool_call_id": tool_call.id
        })
        
        logger.info(f"📋 [TRACE:{trace_id}] Контекст подготовлен: {len(messages)} сообщений")
        logger.info(f"📦 [TRACE:{trace_id}] Данные инструмента: {len(tool_result_content)} символов")
        
        # Получаем финальный ответ через fallback систему
        logger.info(f"🧠 [TRACE:{trace_id}] Запрос финального ответа к LLM с fallback...")
        
        try:
            # Используем fallback систему для финального ответа
            final_llm_response = await self._call_llm_with_fallback(messages, trace_id)
            final_text = final_llm_response["message"].content or "Операция выполнена"
            used_provider = final_llm_response["provider"]
            used_model = final_llm_response["model"]
            
            logger.info(f"✅ [TRACE:{trace_id}] Финальный ответ получен от {used_provider} ({used_model}): {len(final_text)} символов")
            logger.debug(f"📝 [TRACE:{trace_id}] Финальный ответ: {final_text[:200]}...")
        except Exception as e:
            logger.error(f"❌ [TRACE:{trace_id}] Ошибка получения финального ответа: {e}")
            final_text = f"Операция выполнена, но не удалось сформировать ответ: {str(e)}"
        
        return final_text
    
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
    
    def _extract_keywords(self, message: str) -> List[str]:
        """Извлекает ключевые слова из сообщения"""
        keywords = []
        message_lower = message.lower()
        
        # MCP ключевые слова
        mcp_keywords = [
            'приложения', 'apps', 'сервера', 'mcp', 'базы данных',
            'деплой', 'инфраструктура', 'digitalocean', 'supabase'
        ]
        
        # Ключевые слова для изображений
        image_keywords = ['нарисуй', 'создай картинку', 'сгенерируй', 'изображение']
        
        # YouTube ключевые слова
        youtube_keywords = ['youtube.com', 'youtu.be', 'видео', 'субтитры', 'анализ видео']
        
        all_keywords = mcp_keywords + image_keywords + youtube_keywords
        
        for keyword in all_keywords:
            if keyword in message_lower:
                keywords.append(keyword)
                
        return keywords
    
    def _assess_tool_match_confidence(self, message: str, selected_tool: str) -> str:
        """Оценивает уверенность в соответствии инструмента сообщению"""
        message_lower = message.lower()
        
        if selected_tool == "claude_code_direct":
            mcp_indicators = ['приложения', 'apps', 'сервера', 'mcp']
            matches = sum(1 for indicator in mcp_indicators if indicator in message_lower)
            if matches >= 2:
                return "high"
            elif matches >= 1:
                return "medium"
            else:
                return "low"
                
        elif selected_tool == "generate_image":
            image_indicators = ['нарисуй', 'создай', 'сгенерируй']
            matches = sum(1 for indicator in image_indicators if indicator in message_lower)
            return "high" if matches > 0 else "low"
            
        elif selected_tool == "analyze_youtube_video":
            youtube_indicators = ['youtube', 'youtu.be', 'видео']
            matches = sum(1 for indicator in youtube_indicators if indicator in message_lower)
            return "high" if matches > 0 else "low"
            
        elif selected_tool == "echo_tool":
            return "medium"  # Обычно fallback вариант
            
        return "unknown"