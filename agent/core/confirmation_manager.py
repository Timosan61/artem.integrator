"""
Confirmation Manager - управление подтверждениями действий
"""
import asyncio
import logging
from typing import Dict, Optional, List, Any, Callable, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum
import uuid

from ..core.models import (
    ConversationState, 
    ConfirmationRequest,
    ToolType,
    BaseToolParams
)

if TYPE_CHECKING:
    from ..tools.base import BaseTool

logger = logging.getLogger(__name__)


class ConfirmationStatus(str, Enum):
    """Статусы подтверждения"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ConfirmationSession:
    """Сессия подтверждения"""
    
    def __init__(
        self,
        session_id: str,
        user_id: str,
        tool: 'BaseTool',
        params: BaseToolParams,
        expires_at: datetime,
        message: str
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.tool = tool
        self.params = params
        self.expires_at = expires_at
        self.message = message
        self.status = ConfirmationStatus.PENDING
        self.created_at = datetime.now()
        self.responded_at: Optional[datetime] = None
        

class ConfirmationManager:
    """Менеджер подтверждений для критичных операций"""
    
    def __init__(self, default_timeout: int = 300):
        """
        Args:
            default_timeout: Таймаут подтверждения в секундах (по умолчанию 5 минут)
        """
        self.default_timeout = default_timeout
        self._sessions: Dict[str, ConfirmationSession] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> [session_ids]
        
        # Обратные вызовы для UI
        self._on_confirmation_request: Optional[Callable] = None
        self._on_confirmation_response: Optional[Callable] = None
        
        logger.info(f"✅ ConfirmationManager инициализирован (таймаут: {default_timeout}с)")
    
    async def request_confirmation(
        self,
        user_id: str,
        tool: 'BaseTool',
        params: BaseToolParams,
        custom_message: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> str:
        """
        Запрашивает подтверждение у пользователя
        
        Args:
            user_id: ID пользователя
            tool: Инструмент для выполнения
            params: Параметры инструмента
            custom_message: Кастомное сообщение подтверждения
            timeout: Таймаут в секундах
            
        Returns:
            session_id для отслеживания
        """
        # Генерируем ID сессии
        session_id = str(uuid.uuid4())
        
        # Определяем таймаут
        timeout = timeout or self.default_timeout
        expires_at = datetime.now() + timedelta(seconds=timeout)
        
        # Получаем сообщение подтверждения
        if custom_message:
            message = custom_message
        else:
            # Пытаемся получить сообщение от инструмента
            if hasattr(tool, 'get_confirmation_message'):
                message = tool.get_confirmation_message(params)
            else:
                message = self._generate_default_message(tool, params)
        
        # Создаем сессию
        session = ConfirmationSession(
            session_id=session_id,
            user_id=user_id,
            tool=tool,
            params=params,
            expires_at=expires_at,
            message=message
        )
        
        # Сохраняем сессию
        self._sessions[session_id] = session
        
        # Добавляем в список сессий пользователя
        if user_id not in self._user_sessions:
            self._user_sessions[user_id] = []
        self._user_sessions[user_id].append(session_id)
        
        # Вызываем callback если установлен
        if self._on_confirmation_request:
            await self._on_confirmation_request(session)
        
        logger.info(f"🔔 Запрошено подтверждение {session_id} для {tool.metadata.name}")
        
        return session_id
    
    async def handle_response(
        self,
        session_id: str,
        confirmed: bool,
        user_id: Optional[str] = None
    ) -> Optional[Any]:
        """
        Обрабатывает ответ пользователя на подтверждение
        
        Args:
            session_id: ID сессии
            confirmed: Подтверждено или отменено
            user_id: ID пользователя (для проверки)
            
        Returns:
            Результат выполнения инструмента или None
        """
        # Получаем сессию
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"❌ Сессия {session_id} не найдена")
            return None
        
        # Проверяем пользователя
        if user_id and session.user_id != user_id:
            logger.warning(f"❌ Несоответствие пользователя для сессии {session_id}")
            return None
        
        # Проверяем статус
        if session.status != ConfirmationStatus.PENDING:
            logger.warning(f"❌ Сессия {session_id} уже обработана: {session.status}")
            return None
        
        # Проверяем таймаут
        if datetime.now() > session.expires_at:
            session.status = ConfirmationStatus.EXPIRED
            logger.warning(f"⏰ Сессия {session_id} истекла")
            return None
        
        # Обновляем статус
        session.status = ConfirmationStatus.CONFIRMED if confirmed else ConfirmationStatus.CANCELLED
        session.responded_at = datetime.now()
        
        # Вызываем callback
        if self._on_confirmation_response:
            await self._on_confirmation_response(session, confirmed)
        
        # Если подтверждено - выполняем инструмент
        if confirmed:
            logger.info(f"✅ Подтверждение {session_id} принято, выполняем {session.tool.metadata.name}")
            try:
                result = await session.tool.execute(session.params)
                return result
            except Exception as e:
                logger.error(f"❌ Ошибка выполнения после подтверждения: {e}")
                raise
        else:
            logger.info(f"❌ Подтверждение {session_id} отклонено")
            return None
    
    def get_session(self, session_id: str) -> Optional[ConfirmationSession]:
        """Получает сессию по ID"""
        return self._sessions.get(session_id)
    
    def get_pending_sessions(self, user_id: str) -> List[ConfirmationSession]:
        """Получает все ожидающие сессии пользователя"""
        if user_id not in self._user_sessions:
            return []
        
        sessions = []
        for session_id in self._user_sessions[user_id]:
            session = self._sessions.get(session_id)
            if session and session.status == ConfirmationStatus.PENDING:
                # Проверяем таймаут
                if datetime.now() > session.expires_at:
                    session.status = ConfirmationStatus.EXPIRED
                else:
                    sessions.append(session)
        
        return sessions
    
    def cancel_session(self, session_id: str) -> bool:
        """Отменяет сессию"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        if session.status == ConfirmationStatus.PENDING:
            session.status = ConfirmationStatus.CANCELLED
            session.responded_at = datetime.now()
            logger.info(f"🚫 Сессия {session_id} отменена")
            return True
        
        return False
    
    def cleanup_expired(self) -> int:
        """Очищает истекшие сессии"""
        now = datetime.now()
        expired_count = 0
        
        for session_id, session in list(self._sessions.items()):
            if session.expires_at < now and session.status == ConfirmationStatus.PENDING:
                session.status = ConfirmationStatus.EXPIRED
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"🧹 Помечено истекшими {expired_count} сессий")
        
        return expired_count
    
    def set_confirmation_callback(
        self,
        on_request: Optional[Callable] = None,
        on_response: Optional[Callable] = None
    ):
        """
        Устанавливает обратные вызовы для UI
        
        Args:
            on_request: Вызывается при новом запросе подтверждения
            on_response: Вызывается при получении ответа
        """
        if on_request:
            self._on_confirmation_request = on_request
        if on_response:
            self._on_confirmation_response = on_response
    
    def _generate_default_message(self, tool: 'BaseTool', params: BaseToolParams) -> str:
        """Генерирует стандартное сообщение подтверждения"""
        metadata = tool.metadata
        
        message = f"""
🔔 **Требуется подтверждение**

**Инструмент**: {metadata.name}
**Описание**: {metadata.description}

**Параметры операции**:
"""
        
        # Добавляем параметры
        params_dict = params.dict()
        for key, value in params_dict.items():
            if key != 'user_id':  # Не показываем user_id
                message += f"• **{key}**: {value}\n"
        
        message += f"\n⏱ **Ожидаемое время**: {metadata.estimated_time}"
        
        if metadata.requires_confirmation:
            message += "\n\n⚠️ **Внимание**: Эта операция требует обязательного подтверждения"
        
        message += "\n\nПодтвердить выполнение?\n✅ Да / ❌ Нет"
        
        return message
    
    def format_confirmation_buttons(self, session_id: str) -> List[Dict[str, str]]:
        """
        Форматирует кнопки для Telegram
        
        Returns:
            Список кнопок для InlineKeyboardMarkup
        """
        return [
            {
                "text": "✅ Подтвердить",
                "callback_data": f"confirm:{session_id}:yes"
            },
            {
                "text": "❌ Отменить", 
                "callback_data": f"confirm:{session_id}:no"
            }
        ]
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Возвращает статистику по сессиям"""
        total = len(self._sessions)
        by_status = {}
        
        for session in self._sessions.values():
            status = session.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        # Средняя время ответа
        response_times = []
        for session in self._sessions.values():
            if session.responded_at and session.status in [ConfirmationStatus.CONFIRMED, ConfirmationStatus.CANCELLED]:
                delta = (session.responded_at - session.created_at).total_seconds()
                response_times.append(delta)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            "total_sessions": total,
            "by_status": by_status,
            "active_users": len(self._user_sessions),
            "avg_response_time_seconds": avg_response_time
        }


# Глобальный экземпляр менеджера подтверждений
confirmation_manager = ConfirmationManager()