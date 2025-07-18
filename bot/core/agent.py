"""
Обновленный главный агент бота

Координирует работу всех компонентов
"""

import logging
from typing import Optional, Dict, Any, List

from .interfaces import (
    Message, Response, User, MessageType, 
    IMemoryManager, IResponseGenerator, IIntentDetector
)
from .config import config
from .decorators import measure_time, handle_errors
from ..services.memory_manager import ZepMemoryManager, InMemoryManager
from ..services.response_generator import HybridResponseGenerator, SimpleResponseGenerator
from ..services.intent_detector import IntentDetector


logger = logging.getLogger(__name__)


class ArtemAgent:
    """Главный агент бота Артём"""
    
    def __init__(self):
        """Инициализация агента"""
        logger.info("🤖 Инициализация Artem Agent...")
        
        # Инициализируем менеджер памяти
        if config.zep.enabled:
            self.memory_manager = ZepMemoryManager()
        else:
            logger.warning("⚠️ Zep отключен, используем InMemory хранилище")
            self.memory_manager = InMemoryManager()
        
        # Инициализируем генератор ответов
        if config.openai.enabled or config.anthropic.enabled:
            self.response_generator = HybridResponseGenerator()
        else:
            logger.warning("⚠️ AI провайдеры отключены, используем простой генератор")
            self.response_generator = SimpleResponseGenerator()
        
        # Инициализируем детектор намерений
        self.intent_detector = IntentDetector()
        
        # Загружаем инструкции
        self.instructions = self._load_instructions()
        
        logger.info("✅ Artem Agent инициализирован")
    
    @measure_time
    async def process_message(self, message: Message) -> Response:
        """
        Обрабатывает входящее сообщение
        
        Args:
            message: Сообщение для обработки
            
        Returns:
            Response: Ответ на сообщение
        """
        try:
            # Определяем намерение
            intent = await self.intent_detector.detect(message)
            logger.debug(f"🎯 Намерение: {intent['type']} (уверенность: {intent['confidence']})")
            
            # Получаем контекст разговора
            context = await self.memory_manager.get_context(message.user.id)
            
            # Генерируем ответ
            response = await self.response_generator.generate(message, context)
            
            # Сохраняем в память
            await self.memory_manager.add_message(
                user_id=message.user.id,
                message=message,
                response=response
            )
            
            # Добавляем метаданные об обработке
            response.metadata = response.metadata or {}
            response.metadata.update({
                "intent": intent,
                "context_size": len(context)
            })
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            
            # Возвращаем дефолтный ответ при ошибке
            return Response(
                text="Извините, произошла ошибка при обработке вашего сообщения. Попробуйте ещё раз.",
                metadata={"error": str(e)}
            )
    
    async def clear_user_memory(self, user_id: int) -> bool:
        """
        Очищает память пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            bool: Успешность операции
        """
        try:
            await self.memory_manager.clear_memory(user_id)
            logger.info(f"✅ Память очищена для user {user_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка очистки памяти: {e}")
            return False
    
    async def search_user_memory(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """
        Поиск в памяти пользователя
        
        Args:
            user_id: ID пользователя
            query: Поисковый запрос
            
        Returns:
            List[Dict[str, Any]]: Результаты поиска
        """
        try:
            results = await self.memory_manager.search_memory(user_id, query)
            logger.debug(f"🔍 Найдено {len(results)} результатов для '{query}'")
            return results
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в памяти: {e}")
            return []
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Получает статус агента и его компонентов"""
        status = {
            "agent": "online",
            "memory_manager": type(self.memory_manager).__name__,
            "response_generator": type(self.response_generator).__name__,
            "intent_detector": type(self.intent_detector).__name__,
            "services": {
                "openai": config.openai.enabled,
                "anthropic": config.anthropic.enabled,
                "zep": config.zep.enabled
            }
        }
        
        # Проверяем доступность генератора
        try:
            status["generator_available"] = await self.response_generator.is_available()
        except:
            status["generator_available"] = False
        
        return status
    
    def _load_instructions(self) -> Dict[str, Any]:
        """Загружает инструкции агента"""
        # Здесь можно загрузить специфичные инструкции для агента
        return {
            "version": "2.0",
            "updated": "2024-01-20"
        }


class AgentFactory:
    """Фабрика для создания агентов"""
    
    _instance: Optional[ArtemAgent] = None
    
    @classmethod
    def get_agent(cls) -> ArtemAgent:
        """Получает экземпляр агента (синглтон)"""
        if cls._instance is None:
            cls._instance = ArtemAgent()
        return cls._instance
    
    @classmethod
    def reset_agent(cls) -> None:
        """Сбрасывает экземпляр агента"""
        cls._instance = None