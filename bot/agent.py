"""
Agent бота - обертка для обратной совместимости

Использует новую архитектуру, но предоставляет старый интерфейс
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .core.agent import AgentFactory
from .core.interfaces import Message, User, MessageType, UserRole
from .core.config import config
from .agent_legacy import myassistant as LegacyAssistant


logger = logging.getLogger(__name__)


class myassistant:
    """
    Класс-обертка для обратной совместимости
    
    Использует новую архитектуру под капотом, но предоставляет старый API
    """
    
    def __init__(self):
        """Инициализация агента"""
        try:
            # Пробуем использовать новую архитектуру
            self.agent = AgentFactory.get_agent()
            self.use_new_architecture = True
            logger.info("✅ Используется новая архитектура агента")
        except Exception as e:
            # Fallback на старую реализацию
            logger.warning(f"⚠️ Не удалось инициализировать новую архитектуру: {e}")
            logger.info("📦 Используется legacy реализация")
            self.legacy_agent = LegacyAssistant()
            self.use_new_architecture = False
        
        # Для совместимости
        self.openai_client = getattr(self, 'legacy_agent', None) or self
        self.zep_client = getattr(self, 'legacy_agent', None) or self
        self.instruction = config.data_dir / 'instruction.json' if self.use_new_architecture else {}
        self.user_sessions = {}
    
    async def add_to_zep_memory(self, user_id: int, user_name: str, user_message: str, ai_response: str):
        """Добавляет сообщение и ответ в память Zep"""
        if not self.use_new_architecture:
            return await self.legacy_agent.add_to_zep_memory(user_id, user_name, user_message, ai_response)
        
        # Используем новую архитектуру
        try:
            # Создаем объекты Message и User
            user = User(
                id=user_id,
                username=None,
                first_name=user_name,
                last_name=None,
                role=UserRole.USER
            )
            
            message = Message(
                id=0,
                user=user,
                chat_id=user_id,
                text=user_message,
                type=MessageType.TEXT,
                timestamp=datetime.now()
            )
            
            from .core.interfaces import Response
            response = Response(text=ai_response)
            
            # Сохраняем через новый менеджер памяти
            await self.agent.memory_manager.add_message(user_id, message, response)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения в память: {e}")
    
    async def get_zep_memory_context(self, user_id: int, limit: int = 10) -> str:
        """Получает контекст разговора из памяти Zep"""
        if not self.use_new_architecture:
            return await self.legacy_agent.get_zep_memory_context(user_id, limit)
        
        try:
            # Получаем контекст через новый менеджер
            context_list = await self.agent.memory_manager.get_context(user_id, limit)
            
            # Форматируем в старый формат
            context_parts = []
            for msg in context_list:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role == 'user':
                    context_parts.append(f"User: {content}")
                else:
                    context_parts.append(f"Assistant: {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Ошибка получения контекста: {e}")
            return ""
    
    def detect_social_media_intent(self, text: str) -> dict:
        """Определяет намерение пользователя относительно социальных медиа"""
        if not self.use_new_architecture:
            return self.legacy_agent.detect_social_media_intent(text)
        
        # Для новой архитектуры возвращаем упрощенный результат
        # (детекция намерений теперь в IntentDetector)
        text_lower = text.lower()
        platforms = []
        
        if 'youtube' in text_lower or 'ютуб' in text_lower:
            platforms.append('youtube')
        if 'instagram' in text_lower or 'инста' in text_lower:
            platforms.append('instagram')
        if 'tiktok' in text_lower or 'тикток' in text_lower:
            platforms.append('tiktok')
        
        return {
            'has_social_media_intent': len(platforms) > 0,
            'platforms': platforms,
            'actions': [],
            'confidence': 1.0 if platforms else 0.0
        }
    
    async def generate_response(self, user_message: str, user_id: int, user_name: str, 
                              is_admin: bool = False, social_media_response: Optional[str] = None) -> str:
        """Генерирует ответ на сообщение пользователя"""
        if not self.use_new_architecture:
            return await self.legacy_agent.generate_response(
                user_message, user_id, user_name, is_admin, social_media_response
            )
        
        # Если есть готовый ответ от Social Media сервиса
        if social_media_response:
            return social_media_response
        
        try:
            # Создаем объекты для новой архитектуры
            user = User(
                id=user_id,
                username=None,
                first_name=user_name,
                last_name=None,
                role=UserRole.ADMIN if is_admin else UserRole.USER
            )
            
            message = Message(
                id=0,
                user=user,
                chat_id=user_id,
                text=user_message,
                type=MessageType.TEXT,
                timestamp=datetime.now()
            )
            
            # Обрабатываем через новый агент
            response = await self.agent.process_message(message)
            
            # Сохраняем в память (уже сделано в process_message)
            
            return response.text
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Извините, произошла ошибка при обработке вашего сообщения. Попробуйте ещё раз."
    
    def _load_instruction(self) -> Dict[str, Any]:
        """Загружает инструкции"""
        if not self.use_new_architecture:
            return self.legacy_agent._load_instruction()
        
        # Для новой архитектуры инструкции загружаются автоматически
        return {}
    
    def _create_system_message(self, user_name: str, is_admin: bool, intent: dict) -> str:
        """Создает системное сообщение для OpenAI"""
        if not self.use_new_architecture:
            return self.legacy_agent._create_system_message(user_name, is_admin, intent)
        
        # Для новой архитектуры это делается в ResponseGenerator
        return ""
    
    def _get_fallback_response(self, user_message: str, intent: dict) -> str:
        """Возвращает ответ когда OpenAI недоступен"""
        if not self.use_new_architecture:
            return self.legacy_agent._get_fallback_response(user_message, intent)
        
        return "Извините, сервис временно недоступен. Попробуйте позже."
    
    async def ensure_user_exists(self, user_id: int, user_name: str) -> None:
        """Проверяет существование пользователя в Zep и создает если нужно"""
        if not self.use_new_architecture:
            return await self.legacy_agent.ensure_user_exists(user_id, user_name)
        
        # В новой архитектуре это делается автоматически в MemoryManager
        pass
    
    async def clear_user_memory(self, user_id: int) -> bool:
        """Очищает память пользователя"""
        if not self.use_new_architecture:
            return await self.legacy_agent.clear_user_memory(user_id)
        
        try:
            return await self.agent.clear_user_memory(user_id)
        except Exception as e:
            logger.error(f"Ошибка очистки памяти: {e}")
            return False


# Для обратной совместимости экспортируем старое имя класса
MyAssistant = myassistant