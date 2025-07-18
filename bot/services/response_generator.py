"""
Генератор ответов с использованием AI

Отвечает за генерацию ответов на сообщения пользователей
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

import openai
from anthropic import AsyncAnthropic

from ..core.interfaces import IResponseGenerator, Message, Response, ServiceError
from ..core.utils import TextUtils, RetryUtils, FileUtils
from ..core.decorators import measure_time, handle_errors, ensure_service_enabled
from ..core.config import config


logger = logging.getLogger(__name__)


class OpenAIResponseGenerator(IResponseGenerator):
    """Генератор ответов на основе OpenAI"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.enabled = config.openai.enabled
        self.model = config.openai.model
        self.instructions = self._load_instructions()
        
        if self.enabled:
            logger.info(f"✅ OpenAI Response Generator инициализирован (модель: {self.model})")
        else:
            logger.warning("⚠️ OpenAI Response Generator отключен - нет API ключа")
    
    @measure_time
    @ensure_service_enabled('openai')
    @RetryUtils.retry(max_attempts=3, delay=1.0, exceptions=(openai.OpenAIError,))
    async def generate(self, message: Message, context: List[Dict[str, Any]]) -> Response:
        """Генерирует ответ на сообщение"""
        try:
            # Подготавливаем системный промпт
            system_prompt = self._prepare_system_prompt(message.user)
            
            # Подготавливаем сообщения для API
            messages = [{"role": "system", "content": system_prompt}]
            
            # Добавляем контекст
            for ctx_msg in context:
                messages.append({
                    "role": ctx_msg.get("role", "user"),
                    "content": ctx_msg.get("content", "")
                })
            
            # Добавляем текущее сообщение
            messages.append({
                "role": "user",
                "content": message.text or f"[{message.type.value}]"
            })
            
            # Вызываем OpenAI API
            client = openai.AsyncOpenAI(api_key=config.openai.api_key)
            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                user=str(message.user.id)
            )
            
            # Извлекаем ответ
            ai_response = response.choices[0].message.content
            
            # Обрезаем если слишком длинный
            ai_response = TextUtils.truncate(ai_response, config.max_message_length)
            
            logger.debug(f"✅ Сгенерирован ответ для user {message.user.id}")
            
            return Response(
                text=ai_response,
                metadata={
                    "model": self.model,
                    "tokens_used": response.usage.total_tokens if response.usage else 0
                }
            )
            
        except openai.RateLimitError as e:
            logger.error(f"❌ Превышен лимит OpenAI API: {e}")
            raise ServiceError("Превышен лимит запросов. Попробуйте позже.")
        except openai.OpenAIError as e:
            logger.error(f"❌ Ошибка OpenAI API: {e}")
            raise ServiceError(f"Ошибка генерации ответа: {e}")
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка: {e}")
            raise ServiceError(f"Внутренняя ошибка: {e}")
    
    async def is_available(self) -> bool:
        """Проверяет доступность генератора"""
        return self.enabled
    
    def _prepare_system_prompt(self, user) -> str:
        """Подготавливает системный промпт"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""{self.instructions.get('base_prompt', '')}

Текущая дата: {current_date}
Имя пользователя: {user.full_name}
Язык пользователя: {user.language_code or 'ru'}

{self.instructions.get('behavior_rules', '')}"""
        
        return prompt
    
    def _load_instructions(self) -> Dict[str, Any]:
        """Загружает инструкции из файла"""
        instruction_file = config.data_dir / 'instruction.json'
        default_instructions = {
            "base_prompt": "Ты - AI ассистент по имени Артём.",
            "behavior_rules": "Будь вежливым и полезным."
        }
        
        instructions = FileUtils.safe_json_load(instruction_file, default_instructions)
        logger.info(f"📝 Загружены инструкции из {instruction_file}")
        
        return instructions


class AnthropicResponseGenerator(IResponseGenerator):
    """Генератор ответов на основе Anthropic Claude"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.enabled = config.anthropic.enabled
        self.model = config.anthropic.model
        self.client = None
        self.instructions = self._load_instructions()
        
        if self.enabled:
            self.client = AsyncAnthropic(api_key=config.anthropic.api_key)
            logger.info(f"✅ Anthropic Response Generator инициализирован (модель: {self.model})")
        else:
            logger.warning("⚠️ Anthropic Response Generator отключен - нет API ключа")
    
    @measure_time
    @ensure_service_enabled('anthropic')
    @RetryUtils.retry(max_attempts=3, delay=1.0)
    async def generate(self, message: Message, context: List[Dict[str, Any]]) -> Response:
        """Генерирует ответ на сообщение"""
        if not self.client:
            raise ServiceError("Anthropic клиент не инициализирован")
        
        try:
            # Подготавливаем системный промпт
            system_prompt = self._prepare_system_prompt(message.user)
            
            # Подготавливаем сообщения для API
            messages = []
            
            # Добавляем контекст
            for ctx_msg in context:
                messages.append({
                    "role": ctx_msg.get("role", "user"),
                    "content": ctx_msg.get("content", "")
                })
            
            # Добавляем текущее сообщение
            messages.append({
                "role": "user",
                "content": message.text or f"[{message.type.value}]"
            })
            
            # Вызываем Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
                metadata={"user_id": str(message.user.id)}
            )
            
            # Извлекаем ответ
            ai_response = response.content[0].text
            
            # Обрезаем если слишком длинный
            ai_response = TextUtils.truncate(ai_response, config.max_message_length)
            
            logger.debug(f"✅ Сгенерирован ответ Claude для user {message.user.id}")
            
            return Response(
                text=ai_response,
                metadata={
                    "model": self.model,
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка Anthropic API: {e}")
            raise ServiceError(f"Ошибка генерации ответа: {e}")
    
    async def is_available(self) -> bool:
        """Проверяет доступность генератора"""
        return self.enabled and self.client is not None
    
    def _prepare_system_prompt(self, user) -> str:
        """Подготавливает системный промпт"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""{self.instructions.get('base_prompt', '')}

Текущая дата: {current_date}
Имя пользователя: {user.full_name}
Язык пользователя: {user.language_code or 'ru'}

{self.instructions.get('behavior_rules', '')}"""
        
        return prompt
    
    def _load_instructions(self) -> Dict[str, Any]:
        """Загружает инструкции из файла"""
        instruction_file = config.data_dir / 'instruction.json'
        default_instructions = {
            "base_prompt": "Ты - AI ассистент по имени Артём.",
            "behavior_rules": "Будь вежливым и полезным."
        }
        
        instructions = FileUtils.safe_json_load(instruction_file, default_instructions)
        logger.info(f"📝 Загружены инструкции из {instruction_file}")
        
        return instructions


class HybridResponseGenerator(IResponseGenerator):
    """Гибридный генератор, использующий несколько провайдеров"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.generators = []
        
        # Добавляем доступные генераторы
        if config.openai.enabled:
            self.generators.append(OpenAIResponseGenerator())
        
        if config.anthropic.enabled:
            self.generators.append(AnthropicResponseGenerator())
        
        if not self.generators:
            logger.warning("⚠️ Нет доступных генераторов ответов")
    
    async def generate(self, message: Message, context: List[Dict[str, Any]]) -> Response:
        """Генерирует ответ, используя первый доступный генератор"""
        last_error = None
        
        for generator in self.generators:
            try:
                if await generator.is_available():
                    return await generator.generate(message, context)
            except Exception as e:
                logger.warning(f"Генератор {type(generator).__name__} не смог обработать: {e}")
                last_error = e
                continue
        
        if last_error:
            raise last_error
        else:
            raise ServiceError("Нет доступных генераторов ответов")
    
    async def is_available(self) -> bool:
        """Проверяет доступность хотя бы одного генератора"""
        for generator in self.generators:
            if await generator.is_available():
                return True
        return False


class SimpleResponseGenerator(IResponseGenerator):
    """Простой генератор ответов без AI (fallback)"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.responses = {
            "greeting": [
                "Привет! Чем могу помочь?",
                "Здравствуйте! Я готов ответить на ваши вопросы.",
                "Добро пожаловать! Как я могу вам помочь?"
            ],
            "farewell": [
                "До свидания! Был рад помочь.",
                "Удачи! Обращайтесь, если понадобится помощь.",
                "Всего доброго! Заходите ещё."
            ],
            "help": [
                "Я могу помочь вам с различными вопросами. Просто спросите!",
                "Вот что я умею:\n- Отвечать на вопросы\n- Помогать с задачами\n- Предоставлять информацию"
            ],
            "gratitude": [
                "Пожалуйста! Рад был помочь.",
                "Не за что! Обращайтесь ещё.",
                "Всегда рад помочь!"
            ],
            "default": [
                "Извините, я не совсем понял ваш вопрос. Можете переформулировать?",
                "Попробуйте задать вопрос по-другому.",
                "К сожалению, не могу обработать ваш запрос. Попробуйте ещё раз."
            ]
        }
    
    async def generate(self, message: Message, context: List[Dict[str, Any]]) -> Response:
        """Генерирует простой ответ"""
        # Здесь можно добавить логику выбора ответа на основе intent
        # Пока возвращаем дефолтный ответ
        import random
        
        response_text = random.choice(self.responses["default"])
        
        return Response(
            text=response_text,
            metadata={"generator": "simple"}
        )
    
    async def is_available(self) -> bool:
        """Всегда доступен"""
        return True