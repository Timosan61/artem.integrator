"""
Conversation State Manager - управление состояниями разговора
"""
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from enum import Enum
import json

from ..core.models import ConversationState

logger = logging.getLogger(__name__)


class StateType(str, Enum):
    """Типы состояний разговора"""
    NORMAL = "normal"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    MULTI_STEP = "multi_step"


class ConversationStateManager:
    """Менеджер состояний разговоров пользователей"""
    
    def __init__(self, default_ttl: int = 3600):
        """
        Args:
            default_ttl: Время жизни состояния в секундах (по умолчанию 1 час)
        """
        self.default_ttl = default_ttl
        self._states: Dict[str, ConversationState] = {}
        self._state_history: Dict[str, List[ConversationState]] = {}
        
        logger.info(f"📝 ConversationStateManager инициализирован (TTL: {default_ttl}с)")
    
    def create_state(
        self,
        user_id: str,
        state_type: StateType,
        original_message: str,
        tool_to_execute: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> ConversationState:
        """
        Создает новое состояние разговора
        
        Args:
            user_id: ID пользователя
            state_type: Тип состояния
            original_message: Исходное сообщение пользователя
            tool_to_execute: Инструмент для выполнения
            parameters: Параметры для инструмента
            ttl: Время жизни в секундах
            
        Returns:
            Созданное состояние
        """
        # Сохраняем предыдущее состояние в историю
        if user_id in self._states:
            self._add_to_history(user_id, self._states[user_id])
        
        # Определяем время истечения
        ttl = ttl or self.default_ttl
        expires_at = datetime.now() + timedelta(seconds=ttl)
        
        # Создаем новое состояние
        state = ConversationState(
            user_id=user_id,
            state_type=state_type.value,
            original_message=original_message,
            tool_to_execute=tool_to_execute,
            parameters=parameters,
            expires_at=expires_at
        )
        
        # Сохраняем
        self._states[user_id] = state
        
        logger.info(f"📌 Создано состояние {state_type} для пользователя {user_id}")
        
        return state
    
    def get_state(self, user_id: str) -> Optional[ConversationState]:
        """
        Получает текущее состояние пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Текущее состояние или None
        """
        state = self._states.get(user_id)
        
        # Проверяем истечение
        if state and state.expires_at and datetime.now() > state.expires_at:
            logger.info(f"⏰ Состояние пользователя {user_id} истекло")
            self._add_to_history(user_id, state)
            del self._states[user_id]
            return None
        
        return state
    
    def update_state(
        self,
        user_id: str,
        **kwargs
    ) -> Optional[ConversationState]:
        """
        Обновляет существующее состояние
        
        Args:
            user_id: ID пользователя
            **kwargs: Поля для обновления
            
        Returns:
            Обновленное состояние или None
        """
        state = self.get_state(user_id)
        if not state:
            return None
        
        # Обновляем поля
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        
        logger.info(f"📝 Обновлено состояние пользователя {user_id}")
        
        return state
    
    def clear_state(self, user_id: str) -> bool:
        """
        Очищает состояние пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            True если состояние было очищено
        """
        if user_id in self._states:
            self._add_to_history(user_id, self._states[user_id])
            del self._states[user_id]
            logger.info(f"🧹 Очищено состояние пользователя {user_id}")
            return True
        
        return False
    
    def set_normal_state(self, user_id: str) -> ConversationState:
        """Устанавливает нормальное состояние"""
        return self.create_state(
            user_id=user_id,
            state_type=StateType.NORMAL,
            original_message="",
            ttl=60  # Короткое время жизни для нормального состояния
        )
    
    def set_confirmation_state(
        self,
        user_id: str,
        original_message: str,
        tool_name: str,
        parameters: Dict[str, Any],
        confirmation_session_id: str
    ) -> ConversationState:
        """Устанавливает состояние ожидания подтверждения"""
        params = parameters.copy()
        params['confirmation_session_id'] = confirmation_session_id
        
        return self.create_state(
            user_id=user_id,
            state_type=StateType.CONFIRMATION,
            original_message=original_message,
            tool_to_execute=tool_name,
            parameters=params,
            ttl=300  # 5 минут на подтверждение
        )
    
    def set_clarification_state(
        self,
        user_id: str,
        original_message: str,
        clarification_options: List[Dict[str, Any]]
    ) -> ConversationState:
        """Устанавливает состояние ожидания уточнения"""
        return self.create_state(
            user_id=user_id,
            state_type=StateType.CLARIFICATION,
            original_message=original_message,
            parameters={'options': clarification_options},
            ttl=180  # 3 минуты на уточнение
        )
    
    def set_multi_step_state(
        self,
        user_id: str,
        original_message: str,
        current_step: int,
        total_steps: int,
        step_data: Dict[str, Any]
    ) -> ConversationState:
        """Устанавливает состояние многошагового процесса"""
        return self.create_state(
            user_id=user_id,
            state_type=StateType.MULTI_STEP,
            original_message=original_message,
            parameters={
                'current_step': current_step,
                'total_steps': total_steps,
                'step_data': step_data
            },
            ttl=600  # 10 минут на многошаговый процесс
        )
    
    def _add_to_history(self, user_id: str, state: ConversationState):
        """Добавляет состояние в историю"""
        if user_id not in self._state_history:
            self._state_history[user_id] = []
        
        # Ограничиваем историю последними 10 состояниями
        history = self._state_history[user_id]
        history.append(state)
        if len(history) > 10:
            history.pop(0)
    
    def get_state_history(self, user_id: str, limit: int = 5) -> List[ConversationState]:
        """
        Получает историю состояний пользователя
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество записей
            
        Returns:
            Список предыдущих состояний
        """
        history = self._state_history.get(user_id, [])
        return history[-limit:] if history else []
    
    def cleanup_expired(self) -> int:
        """Очищает истекшие состояния"""
        now = datetime.now()
        expired_users = []
        
        for user_id, state in self._states.items():
            if state.expires_at and now > state.expires_at:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            self.clear_state(user_id)
        
        if expired_users:
            logger.info(f"🧹 Очищено {len(expired_users)} истекших состояний")
        
        return len(expired_users)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику по состояниям"""
        by_type = {}
        
        for state in self._states.values():
            state_type = state.state_type
            by_type[state_type] = by_type.get(state_type, 0) + 1
        
        return {
            "active_states": len(self._states),
            "by_type": by_type,
            "users_with_history": len(self._state_history),
            "total_history_records": sum(len(h) for h in self._state_history.values())
        }
    
    def export_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Экспортирует состояние в словарь для сериализации"""
        state = self.get_state(user_id)
        if not state:
            return None
        
        return {
            "user_id": state.user_id,
            "state_type": state.state_type,
            "original_message": state.original_message,
            "tool_to_execute": state.tool_to_execute,
            "parameters": state.parameters,
            "created_at": state.created_at.isoformat(),
            "expires_at": state.expires_at.isoformat() if state.expires_at else None
        }
    
    def import_state(self, state_data: Dict[str, Any]) -> Optional[ConversationState]:
        """Импортирует состояние из словаря"""
        try:
            # Восстанавливаем даты
            created_at = datetime.fromisoformat(state_data["created_at"])
            expires_at = None
            if state_data.get("expires_at"):
                expires_at = datetime.fromisoformat(state_data["expires_at"])
            
            # Создаем состояние
            state = ConversationState(
                user_id=state_data["user_id"],
                state_type=state_data["state_type"],
                original_message=state_data["original_message"],
                tool_to_execute=state_data.get("tool_to_execute"),
                parameters=state_data.get("parameters"),
                created_at=created_at,
                expires_at=expires_at
            )
            
            # Сохраняем
            self._states[state.user_id] = state
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Ошибка импорта состояния: {e}")
            return None


# Глобальный экземпляр менеджера состояний
conversation_state_manager = ConversationStateManager()