"""
Preference Manager - управление предпочтениями пользователей для обучения агента
"""
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from collections import defaultdict

from ..core.models import ToolType, UserPreference
from .intents import Intent

logger = logging.getLogger(__name__)


class PreferencePattern:
    """Паттерн предпочтения пользователя"""
    
    def __init__(
        self,
        user_id: str,
        intent: Intent,
        tool_type: ToolType,
        confidence_threshold: float = 0.8
    ):
        self.user_id = user_id
        self.intent = intent
        self.tool_type = tool_type
        self.confidence_threshold = confidence_threshold
        self.usage_count = 0
        self.success_count = 0
        self.last_used = datetime.now()
        self.created_at = datetime.now()
        
        # Примеры использования для обучения
        self.examples: List[Dict[str, Any]] = []
    
    def add_usage(self, success: bool, message: str, tool_params: Optional[Dict] = None):
        """Добавляет использование паттерна"""
        self.usage_count += 1
        if success:
            self.success_count += 1
        self.last_used = datetime.now()
        
        # Сохраняем пример
        self.examples.append({
            "message": message,
            "success": success,
            "tool_params": tool_params,
            "timestamp": datetime.now().isoformat()
        })
        
        # Ограничиваем количество примеров
        if len(self.examples) > 10:
            self.examples = self.examples[-10:]
    
    @property
    def success_rate(self) -> float:
        """Процент успешных использований"""
        if self.usage_count == 0:
            return 0.0
        return self.success_count / self.usage_count
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для сохранения"""
        return {
            "user_id": self.user_id,
            "intent": self.intent.value,
            "tool_type": self.tool_type.value,
            "confidence_threshold": self.confidence_threshold,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "last_used": self.last_used.isoformat(),
            "created_at": self.created_at.isoformat(),
            "examples": self.examples
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PreferencePattern':
        """Создает из словаря"""
        pattern = cls(
            user_id=data["user_id"],
            intent=Intent(data["intent"]),
            tool_type=ToolType(data["tool_type"]),
            confidence_threshold=data.get("confidence_threshold", 0.8)
        )
        pattern.usage_count = data.get("usage_count", 0)
        pattern.success_count = data.get("success_count", 0)
        pattern.last_used = datetime.fromisoformat(data["last_used"])
        pattern.created_at = datetime.fromisoformat(data["created_at"])
        pattern.examples = data.get("examples", [])
        return pattern


class PreferenceManager:
    """Менеджер предпочтений пользователей"""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = Path(storage_path or "agent/data/user_preferences.json")
        self.preferences: Dict[str, Dict[str, PreferencePattern]] = {}
        self.learning_threshold = 3  # Минимум использований для обучения
        self.preference_ttl_days = 30  # Срок жизни предпочтения
        
        # Загружаем существующие предпочтения
        self._load_preferences()
        
        # Статистика для анализа
        self.stats = defaultdict(lambda: defaultdict(int))
        
        logger.info("🧠 PreferenceManager инициализирован")
    
    def _load_preferences(self):
        """Загружает предпочтения из файла"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for user_id, user_prefs in data.items():
                    self.preferences[user_id] = {}
                    for key, pref_data in user_prefs.items():
                        pattern = PreferencePattern.from_dict(pref_data)
                        self.preferences[user_id][key] = pattern
                
                logger.info(f"📚 Загружено предпочтений: {sum(len(p) for p in self.preferences.values())}")
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки предпочтений: {e}")
    
    def _save_preferences(self):
        """Сохраняет предпочтения в файл"""
        try:
            # Создаем директорию если не существует
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Конвертируем в сохраняемый формат
            data = {}
            for user_id, user_prefs in self.preferences.items():
                data[user_id] = {}
                for key, pattern in user_prefs.items():
                    data[user_id][key] = pattern.to_dict()
            
            # Сохраняем
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug("💾 Предпочтения сохранены")
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения предпочтений: {e}")
    
    def record_choice(
        self,
        user_id: str,
        message: str,
        intent: Intent,
        tool_type: ToolType,
        success: bool,
        tool_params: Optional[Dict] = None
    ):
        """Записывает выбор пользователя"""
        # Создаем ключ для паттерна
        pattern_key = f"{intent.value}:{tool_type.value}"
        
        # Инициализируем структуры если нужно
        if user_id not in self.preferences:
            self.preferences[user_id] = {}
        
        # Получаем или создаем паттерн
        if pattern_key not in self.preferences[user_id]:
            self.preferences[user_id][pattern_key] = PreferencePattern(
                user_id=user_id,
                intent=intent,
                tool_type=tool_type
            )
        
        pattern = self.preferences[user_id][pattern_key]
        pattern.add_usage(success, message, tool_params)
        
        # Обновляем статистику
        self.stats[user_id]["total_choices"] += 1
        if success:
            self.stats[user_id]["successful_choices"] += 1
        
        # Сохраняем если достигнут порог обучения
        if pattern.usage_count % self.learning_threshold == 0:
            self._save_preferences()
            logger.info(f"🎯 Обновлено предпочтение {pattern_key} для пользователя {user_id}")
    
    def get_preferred_tool(
        self,
        user_id: str,
        intent: Intent,
        available_tools: List[ToolType]
    ) -> Optional[Tuple[ToolType, float]]:
        """
        Получает предпочитаемый инструмент для намерения
        
        Returns:
            Tuple[ToolType, confidence] или None
        """
        if user_id not in self.preferences:
            return None
        
        best_tool = None
        best_score = 0.0
        
        for tool_type in available_tools:
            pattern_key = f"{intent.value}:{tool_type.value}"
            
            if pattern_key in self.preferences[user_id]:
                pattern = self.preferences[user_id][pattern_key]
                
                # Проверяем актуальность
                if self._is_pattern_valid(pattern):
                    # Вычисляем score на основе использований и успешности
                    score = self._calculate_pattern_score(pattern)
                    
                    if score > best_score and score >= pattern.confidence_threshold:
                        best_tool = tool_type
                        best_score = score
        
        if best_tool:
            logger.debug(f"🎯 Найдено предпочтение для {user_id}: {intent.value} -> {best_tool.value} (score: {best_score:.2f})")
            return (best_tool, best_score)
        
        return None
    
    def _is_pattern_valid(self, pattern: PreferencePattern) -> bool:
        """Проверяет актуальность паттерна"""
        # Проверяем TTL
        age_days = (datetime.now() - pattern.last_used).days
        if age_days > self.preference_ttl_days:
            return False
        
        # Проверяем минимальное количество использований
        if pattern.usage_count < self.learning_threshold:
            return False
        
        # Проверяем успешность
        if pattern.success_rate < 0.5:  # Минимум 50% успешности
            return False
        
        return True
    
    def _calculate_pattern_score(self, pattern: PreferencePattern) -> float:
        """Вычисляет score паттерна"""
        # Базовый score - процент успешности
        base_score = pattern.success_rate
        
        # Бонус за частоту использования
        usage_bonus = min(pattern.usage_count / 20, 0.2)  # Максимум +0.2
        
        # Штраф за давность
        age_days = (datetime.now() - pattern.last_used).days
        age_penalty = age_days / self.preference_ttl_days * 0.3  # Максимум -0.3
        
        return min(base_score + usage_bonus - age_penalty, 1.0)
    
    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Получает статистику пользователя"""
        if user_id not in self.preferences:
            return {
                "total_patterns": 0,
                "total_choices": 0,
                "successful_choices": 0,
                "success_rate": 0.0,
                "favorite_tools": []
            }
        
        # Считаем статистику
        patterns = self.preferences[user_id]
        total_usage = sum(p.usage_count for p in patterns.values())
        total_success = sum(p.success_count for p in patterns.values())
        
        # Находим любимые инструменты
        tool_usage = defaultdict(int)
        for pattern in patterns.values():
            tool_usage[pattern.tool_type.value] += pattern.usage_count
        
        favorite_tools = sorted(
            tool_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        return {
            "total_patterns": len(patterns),
            "total_choices": self.stats[user_id]["total_choices"],
            "successful_choices": self.stats[user_id]["successful_choices"],
            "success_rate": total_success / total_usage if total_usage > 0 else 0.0,
            "favorite_tools": favorite_tools,
            "active_patterns": sum(1 for p in patterns.values() if self._is_pattern_valid(p))
        }
    
    def cleanup_old_preferences(self):
        """Очищает устаревшие предпочтения"""
        cleaned = 0
        
        for user_id in list(self.preferences.keys()):
            user_prefs = self.preferences[user_id]
            
            # Удаляем устаревшие паттерны
            for key in list(user_prefs.keys()):
                pattern = user_prefs[key]
                if not self._is_pattern_valid(pattern):
                    del user_prefs[key]
                    cleaned += 1
            
            # Удаляем пользователя если нет паттернов
            if not user_prefs:
                del self.preferences[user_id]
        
        if cleaned > 0:
            self._save_preferences()
            logger.info(f"🧹 Очищено устаревших предпочтений: {cleaned}")
    
    def export_learning_data(self) -> List[Dict[str, Any]]:
        """Экспортирует данные для обучения модели"""
        learning_data = []
        
        for user_id, patterns in self.preferences.items():
            for pattern in patterns.values():
                if self._is_pattern_valid(pattern) and pattern.examples:
                    for example in pattern.examples:
                        if example["success"]:  # Только успешные примеры
                            learning_data.append({
                                "message": example["message"],
                                "intent": pattern.intent.value,
                                "tool_type": pattern.tool_type.value,
                                "confidence": pattern.success_rate,
                                "user_id": user_id
                            })
        
        return learning_data


# Глобальный экземпляр менеджера предпочтений
preference_manager = PreferenceManager()