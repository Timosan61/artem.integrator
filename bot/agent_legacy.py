"""
Legacy agent.py - сохранен для обратной совместимости

Этот файл содержит оригинальную реализацию myassistant
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import openai
from zep_cloud.client import AsyncZep
from zep_cloud.types import Message

from .config import INSTRUCTION_FILE, OPENAI_API_KEY, OPENAI_MODEL, ZEP_API_KEY

# Настройка логирования
logger = logging.getLogger(__name__)


class myassistant:
    def __init__(self):
        # Инициализируем OpenAI клиент если API ключ доступен
        if OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
            print("✅ OpenAI клиент инициализирован")
        else:
            self.openai_client = None
            print("⚠️ OpenAI API ключ не найден, используется упрощенный режим")
        
        # Инициализируем Zep клиент если API ключ доступен
        if ZEP_API_KEY and ZEP_API_KEY != "test_key":
            try:
                self.zep_client = AsyncZep(api_key=ZEP_API_KEY)
                print(f"✅ Zep клиент инициализирован с ключом длиной {len(ZEP_API_KEY)} символов")
                print(f"🔑 Zep API Key начинается с: {ZEP_API_KEY[:8]}...")
            except Exception as e:
                print(f"❌ Ошибка инициализации Zep клиента: {e}")
                self.zep_client = None
        else:
            self.zep_client = None
            if not ZEP_API_KEY:
                print("⚠️ ZEP_API_KEY не установлен, используется локальная память")
            else:
                print(f"⚠️ ZEP_API_KEY имеет значение 'test_key', используется локальная память")
        self.instruction = self._load_instruction()
        self.user_sessions = {}  # Резервное хранение сессий в памяти
    
    def _load_instruction(self) -> Dict[str, Any]:
        try:
            with open(INSTRUCTION_FILE, 'r', encoding='utf-8') as f:
                instruction = json.load(f)
                logger.info(f"✅ Инструкции успешно загружены из {INSTRUCTION_FILE}")
                logger.info(f"📝 Последнее обновление: {instruction.get('last_updated', 'неизвестно')}")
                return instruction
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки инструкций: {e}")
            # Возвращаем базовые инструкции если файл не найден
            return {
                "instructions": {
                    "main": "Ты - AI-консультант по имени Артём. Твоя задача помогать пользователям с их вопросами.",
                    "behavior": [
                        "Будь дружелюбным и профессиональным",
                        "Давай полезные и точные ответы",
                        "Если не знаешь ответа - честно скажи об этом"
                    ]
                },
                "name": "Артём"
            }
    
    async def add_to_zep_memory(self, user_id: int, user_name: str, user_message: str, ai_response: str):
        """Добавляет сообщение и ответ в память Zep"""
        if not self.zep_client:
            # Сохраняем в локальную память если Zep недоступен
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append({
                "user": user_message,
                "assistant": ai_response,
                "timestamp": datetime.now().isoformat()
            })
            # Ограничиваем историю последними 20 сообщениями
            if len(self.user_sessions[user_id]) > 20:
                self.user_sessions[user_id] = self.user_sessions[user_id][-20:]
            return
        
        session_id = f"telegram_user_{user_id}"
        
        try:
            # Проверяем существование сессии
            try:
                await self.zep_client.memory.get(session_id=session_id)
            except Exception:
                # Сессия не существует, создаем новую
                from zep_cloud import Session
                session = Session(
                    session_id=session_id,
                    user_id=str(user_id),
                    metadata={
                        "user_name": user_name,
                        "platform": "telegram",
                        "created_at": datetime.now().isoformat()
                    }
                )
                await self.zep_client.sessions.add(session=session)
                logger.info(f"✅ Создана новая сессия для пользователя {user_name} (ID: {user_id})")
            
            # Добавляем сообщения в память
            from zep_cloud import Memory
            messages = [
                Message(
                    role="user",
                    role_type="user",
                    content=user_message,
                    metadata={"timestamp": datetime.now().isoformat()}
                ),
                Message(
                    role="assistant",
                    role_type="assistant", 
                    content=ai_response,
                    metadata={"timestamp": datetime.now().isoformat()}
                )
            ]
            
            memory = Memory(messages=messages)
            await self.zep_client.memory.add(session_id=session_id, memory=memory)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при сохранении в Zep: {e}")
            # Fallback на локальную память
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = []
            self.user_sessions[user_id].append({
                "user": user_message,
                "assistant": ai_response,
                "timestamp": datetime.now().isoformat()
            })
    
    async def get_zep_memory_context(self, user_id: int, limit: int = 10) -> str:
        """Получает контекст разговора из памяти Zep"""
        if not self.zep_client:
            # Возвращаем из локальной памяти
            if user_id in self.user_sessions:
                context = []
                for msg in self.user_sessions[user_id][-limit:]:
                    context.append(f"User: {msg['user']}")
                    context.append(f"Assistant: {msg['assistant']}")
                return "\n".join(context)
            return ""
        
        session_id = f"telegram_user_{user_id}"
        
        try:
            memory = await self.zep_client.memory.get(session_id=session_id, limit=limit)
            
            if not memory or not memory.messages:
                return ""
            
            # Последние limit сессий
            recent_sessions = memory.messages[-limit*2:] if memory.messages else []
            
            context_parts = []
            for msg in recent_sessions:
                if msg.role == "user":
                    context_parts.append(f"User: {msg.content}")
                else:
                    context_parts.append(f"Assistant: {msg.content}")
            
            return "\n".join(context_parts[-6:])  # Последние 6 сообщений (3 пары)
            
        except Exception as e:
            logger.error(f"❌ Ошибка при получении контекста из Zep: {e}")
            # Fallback на локальную память
            if user_id in self.user_sessions:
                context = []
                for msg in self.user_sessions[user_id][-limit:]:
                    context.append(f"User: {msg['user']}")
                    context.append(f"Assistant: {msg['assistant']}")
                return "\n".join(context)
            return ""
    
    def detect_social_media_intent(self, text: str) -> dict:
        """Определяет намерение пользователя относительно социальных медиа"""
        text_lower = text.lower()
        
        # Ключевые слова для разных платформ
        keywords = {
            'youtube': ['youtube', 'ютуб', 'видео', 'ролик', 'канал', 'подписчик', 
                       'просмотр', 'лайк', 'дизлайк', 'комментарий', 'трек', 'клип',
                       'стрим', 'stream', 'влог', 'vlog', 'контент'],
            'instagram': ['instagram', 'инстаграм', 'инста', 'пост', 'сторис', 'stories',
                         'рилс', 'reels', 'фото', 'подписчик', 'лайк', 'хештег', 'hashtag'],
            'tiktok': ['tiktok', 'тикток', 'тик ток', 'короткое видео', 'челлендж',
                      'challenge', 'тренд', 'trend', 'дуэт', 'duet']
        }
        
        # Проверяем наличие ключевых слов
        detected_platforms = []
        for platform, platform_keywords in keywords.items():
            for keyword in platform_keywords:
                if keyword in text_lower:
                    detected_platforms.append(platform)
                    break
        
        # Определяем тип действия
        actions = {
            'analyze': ['анализ', 'проанализируй', 'посмотри', 'проверь', 'изучи', 
                       'статистика', 'метрики', 'показатели'],
            'download': ['скачай', 'загрузи', 'download', 'сохрани'],
            'create': ['создай', 'сделай', 'сгенерируй', 'придумай', 'напиши'],
            'optimize': ['оптимизируй', 'улучши', 'повысь', 'увеличь'],
            'search': ['найди', 'поищи', 'search', 'покажи']
        }
        
        detected_actions = []
        for action, action_keywords in actions.items():
            for keyword in action_keywords:
                if keyword in text_lower:
                    detected_actions.append(action)
                    break
        
        return {
            'has_social_media_intent': len(detected_platforms) > 0,
            'platforms': detected_platforms,
            'actions': detected_actions,
            'confidence': min(len(detected_platforms) + len(detected_actions), 5) / 5.0
        }
    
    async def generate_response(self, user_message: str, user_id: int, user_name: str, 
                              is_admin: bool = False, social_media_response: Optional[str] = None) -> str:
        # Проверяем намерение пользователя
        intent = self.detect_social_media_intent(user_message)
        
        # Если есть готовый ответ от Social Media сервиса
        if social_media_response:
            return social_media_response
            
        if not self.openai_client:
            return self._get_fallback_response(user_message, intent)
        
        try:
            # Получаем контекст разговора
            context = await self.get_zep_memory_context(user_id)
            
            # Формируем системное сообщение
            system_message = self._create_system_message(user_name, is_admin, intent)
            
            # Подготавливаем сообщения для API
            messages = [
                {"role": "system", "content": system_message}
            ]
            
            # Добавляем контекст если есть
            if context:
                messages.append({"role": "system", "content": f"Контекст предыдущего разговора:\n{context}"})
            
            # Добавляем сообщение пользователя
            messages.append({"role": "user", "content": user_message})
            
            # Генерируем ответ через OpenAI
            response = await self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=800
            )
            
            ai_response = response.choices[0].message.content
            
            # Сохраняем в память
            await self.add_to_zep_memory(user_id, user_name, user_message, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации ответа: {e}")
            return self._get_fallback_response(user_message, intent)
    
    def _create_system_message(self, user_name: str, is_admin: bool, intent: dict) -> str:
        """Создает системное сообщение для OpenAI"""
        base_instruction = self.instruction.get('instructions', {}).get('main', '')
        behavior_rules = self.instruction.get('instructions', {}).get('behavior', [])
        name = self.instruction.get('name', 'Артём')
        
        system_message = f"{base_instruction}\n\nТвое имя: {name}\n"
        system_message += f"Имя пользователя: {user_name}\n"
        
        if is_admin:
            system_message += "Статус пользователя: Администратор (имеет расширенные права)\n"
        
        if behavior_rules:
            system_message += "\nПравила поведения:\n"
            for rule in behavior_rules:
                system_message += f"- {rule}\n"
        
        # Добавляем информацию о намерениях если обнаружены
        if intent['has_social_media_intent']:
            system_message += f"\nПользователь интересуется социальными медиа: {', '.join(intent['platforms'])}\n"
            if intent['actions']:
                system_message += f"Возможные действия: {', '.join(intent['actions'])}\n"
            system_message += "Подскажи пользователю, что для работы с социальными медиа нужны специальные команды.\n"
        
        return system_message
    
    def _get_fallback_response(self, user_message: str, intent: dict) -> str:
        """Возвращает ответ когда OpenAI недоступен"""
        if intent['has_social_media_intent']:
            platforms_str = ", ".join(intent['platforms'])
            return f"Я вижу, что вы интересуетесь {platforms_str}. К сожалению, сейчас я работаю в ограниченном режиме. Попробуйте позже или обратитесь к администратору."
        
        responses = [
            "Извините, сейчас я работаю в ограниченном режиме. Попробуйте переформулировать вопрос или обратитесь позже.",
            "К сожалению, я временно не могу дать развернутый ответ. Пожалуйста, попробуйте позже.",
            "Я понимаю ваш вопрос, но сейчас могу работать только в базовом режиме. Обратитесь к администратору для полного функционала."
        ]
        
        # Простая логика выбора ответа
        if "?" in user_message:
            return responses[0]
        elif len(user_message) > 50:
            return responses[1]
        else:
            return responses[2]
    
    async def ensure_user_exists(self, user_id: int, user_name: str) -> None:
        """Проверяет существование пользователя в Zep и создает если нужно"""
        if not self.zep_client:
            return
            
        try:
            # Пытаемся получить пользователя
            user = await self.zep_client.users.get(user_id=str(user_id))
            logger.info(f"✅ Пользователь {user_name} (ID: {user_id}) уже существует в Zep")
        except Exception:
            # Пользователь не существует, создаем
            try:
                from zep_cloud import User
                user = User(
                    user_id=str(user_id),
                    first_name=user_name,
                    metadata={
                        "platform": "telegram",
                        "created_at": datetime.now().isoformat()
                    }
                )
                await self.zep_client.users.add(user=user)
                logger.info(f"✅ Создан новый пользователь в Zep: {user_name} (ID: {user_id})")
            except Exception as e:
                logger.error(f"❌ Ошибка создания пользователя в Zep: {e}")
    
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память пользователя"""
        if self.zep_client:
            session_id = f"telegram_user_{user_id}"
            try:
                await self.zep_client.memory.delete(session_id=session_id)
                logger.info(f"✅ Память пользователя {user_id} очищена в Zep")
                return True
            except Exception as e:
                logger.error(f"❌ Ошибка очистки памяти в Zep: {e}")
        
        # Очищаем локальную память
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            logger.info(f"✅ Локальная память пользователя {user_id} очищена")
            return True
            
        return False