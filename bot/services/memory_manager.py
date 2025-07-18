"""
Менеджер памяти для работы с Zep

Отвечает за сохранение и извлечение контекста разговоров
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from zep_cloud.client import AsyncZep
from zep_cloud import Message as ZepMessage

from ..core.interfaces import IMemoryManager, Message, Response, ServiceError
from ..core.utils import RetryUtils, CacheUtils
from ..core.decorators import measure_time, handle_errors
from ..core.config import config


logger = logging.getLogger(__name__)


class ZepMemoryManager(IMemoryManager):
    """Менеджер памяти на основе Zep"""
    
    def __init__(self):
        """Инициализация менеджера памяти"""
        self.client = None
        self.enabled = False
        
        if config.zep.enabled and config.zep.api_key:
            try:
                self.client = AsyncZep(
                    api_key=config.zep.api_key
                )
                self.enabled = True
                logger.info("✅ Zep Memory Manager инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Zep: {e}")
        else:
            logger.warning("⚠️ Zep Memory Manager отключен - нет API ключа")
    
    @measure_time
    @RetryUtils.retry(max_attempts=3, delay=1.0)
    async def add_message(
        self,
        user_id: int,
        message: Message,
        response: Optional[Response] = None
    ) -> None:
        """Добавляет сообщение и ответ в память"""
        if not self.enabled or not self.client:
            logger.debug(f"Zep отключен, пропускаем сохранение для user {user_id}")
            return
        
        try:
            session_id = self._get_session_id(user_id)
            
            # Создаем сессию если не существует
            await self._ensure_session_exists(session_id, user_id, message.user.full_name)
            
            # Подготавливаем сообщения
            messages = []
            
            # Добавляем сообщение пользователя
            user_message = ZepMessage(
                role="user",
                role_type="user",
                content=message.text or f"[{message.type.value}]",
                metadata={
                    "message_id": message.id,
                    "message_type": message.type.value,
                    "timestamp": message.timestamp.isoformat()
                }
            )
            messages.append(user_message)
            
            # Добавляем ответ ассистента если есть
            if response:
                assistant_message = ZepMessage(
                    role="assistant",
                    role_type="assistant",
                    content=response.text,
                    metadata={
                        "timestamp": datetime.now().isoformat()
                    }
                )
                messages.append(assistant_message)
            
            # Сохраняем в Zep
            await self.client.memory.add(session_id=session_id, messages=messages)
            
            logger.debug(f"✅ Сохранено {len(messages)} сообщений для user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения в Zep для user {user_id}: {e}")
            raise ServiceError(f"Ошибка сохранения памяти: {e}")
    
    @measure_time
    @CacheUtils.ttl_cache(ttl_seconds=60)
    async def get_context(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает контекст разговора из памяти"""
        if not self.enabled or not self.client:
            logger.debug(f"Zep отключен, возвращаем пустой контекст для user {user_id}")
            return []
        
        try:
            session_id = self._get_session_id(user_id)
            
            # Получаем память из Zep
            memory = await self.client.memory.get(
                session_id=session_id,
                lastn=limit
            )
            
            if not memory or not memory.messages:
                logger.debug(f"Нет истории для user {user_id}")
                return []
            
            # Преобразуем в нужный формат
            context = []
            for msg in memory.messages:
                context_item = {
                    "role": msg.role or "user",
                    "content": msg.content or "",
                    "timestamp": msg.metadata.get("timestamp") if msg.metadata else None
                }
                context.append(context_item)
            
            logger.debug(f"✅ Получено {len(context)} сообщений контекста для user {user_id}")
            return context
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения контекста для user {user_id}: {e}")
            return []
    
    async def clear_memory(self, user_id: int) -> None:
        """Очищает память пользователя"""
        if not self.enabled or not self.client:
            return
        
        try:
            session_id = self._get_session_id(user_id)
            await self.client.memory.delete(session_id=session_id)
            logger.info(f"✅ Память очищена для user {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка очистки памяти для user {user_id}: {e}")
    
    @measure_time
    async def search_memory(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """Поиск в памяти по запросу"""
        if not self.enabled or not self.client:
            return []
        
        try:
            session_id = self._get_session_id(user_id)
            
            # Выполняем поиск
            results = await self.client.memory.search(
                session_id=session_id,
                text=query,
                limit=5
            )
            
            if not results or not hasattr(results, 'results'):
                return []
            
            # Преобразуем результаты
            search_results = []
            for result in results.results:
                if hasattr(result, 'message') and result.message:
                    search_results.append({
                        "content": result.message.content,
                        "role": result.message.role,
                        "score": getattr(result, 'score', 0),
                        "timestamp": result.message.metadata.get("timestamp") if hasattr(result.message, 'metadata') and result.message.metadata else None
                    })
            
            logger.debug(f"✅ Найдено {len(search_results)} результатов для запроса '{query}'")
            return search_results
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска в памяти: {e}")
            return []
    
    async def get_session_summary(self, user_id: int) -> Optional[str]:
        """Получает саммари сессии"""
        if not self.enabled or not self.client:
            return None
        
        try:
            session_id = self._get_session_id(user_id)
            memory = await self.client.memory.get(session_id=session_id)
            
            if memory and memory.summary:
                return memory.summary.content
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения саммари: {e}")
            return None
    
    def _get_session_id(self, user_id: int) -> str:
        """Генерирует ID сессии для пользователя"""
        return f"telegram_user_{user_id}"
    
    async def _ensure_session_exists(self, session_id: str, user_id: int, user_name: str) -> None:
        """Проверяет и создает сессию если не существует"""
        try:
            # Пробуем получить сессию
            await self.client.memory.get_session(session_id=session_id)
        except Exception:
            # Сессия не существует, создаем
            try:
                await self.client.memory.add_session(
                    session_id=session_id,
                    user_id=str(user_id),
                    metadata={
                        "user_name": user_name,
                        "platform": "telegram", 
                        "created_at": datetime.now().isoformat()
                    }
                )
                logger.debug(f"✅ Создана новая сессия {session_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка создания сессии: {e}")


class InMemoryManager(IMemoryManager):
    """Простой менеджер памяти в оперативной памяти (fallback)"""
    
    def __init__(self, max_messages_per_user: int = 100):
        self.memory: Dict[int, List[Dict[str, Any]]] = {}
        self.max_messages = max_messages_per_user
    
    async def add_message(
        self,
        user_id: int,
        message: Message,
        response: Optional[Response] = None
    ) -> None:
        """Добавляет сообщение в память"""
        if user_id not in self.memory:
            self.memory[user_id] = []
        
        # Добавляем сообщение пользователя
        self.memory[user_id].append({
            "role": "user",
            "content": message.text or f"[{message.type.value}]",
            "timestamp": message.timestamp.isoformat()
        })
        
        # Добавляем ответ если есть
        if response:
            self.memory[user_id].append({
                "role": "assistant",
                "content": response.text,
                "timestamp": datetime.now().isoformat()
            })
        
        # Ограничиваем размер истории
        if len(self.memory[user_id]) > self.max_messages * 2:
            self.memory[user_id] = self.memory[user_id][-self.max_messages * 2:]
    
    async def get_context(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получает контекст разговора"""
        if user_id not in self.memory:
            return []
        
        return self.memory[user_id][-limit * 2:]  # Умножаем на 2 для пар user/assistant
    
    async def clear_memory(self, user_id: int) -> None:
        """Очищает память пользователя"""
        if user_id in self.memory:
            del self.memory[user_id]
    
    async def search_memory(self, user_id: int, query: str) -> List[Dict[str, Any]]:
        """Простой поиск в памяти"""
        if user_id not in self.memory:
            return []
        
        results = []
        query_lower = query.lower()
        
        for msg in self.memory[user_id]:
            if query_lower in msg.get("content", "").lower():
                results.append(msg)
        
        return results[:5]  # Максимум 5 результатов