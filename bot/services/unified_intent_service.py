"""
Унифицированный сервис определения интентов

Объединяет функциональность intent_detector.py и intent_classifier.py
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime

from ..core.interfaces import Message, IIntentDetector
from ..core.decorators import measure_time

logger = logging.getLogger(__name__)


class UnifiedIntentType(str, Enum):
    """Все типы намерений в одном месте"""
    # Базовые интенты
    GREETING = "greeting"
    FAREWELL = "farewell"
    HELP = "help"
    QUESTION = "question"
    COMMAND = "command"
    GRATITUDE = "gratitude"
    COMPLAINT = "complaint"
    UNKNOWN = "unknown"
    
    # Специализированные интенты
    MCP_COMMAND = "mcp_command"
    YOUTUBE_ANALYSIS = "youtube_analysis"
    SOCIAL_MEDIA = "social_media"
    YOUTUBE_URL = "youtube_url"
    
    # Служебные интенты
    CLARIFICATION_NEEDED = "clarification_needed"
    GENERAL_CHAT = "general_chat"


class UnifiedIntentService(IIntentDetector):
    """
    Единый сервис для определения намерений пользователя
    
    Объединяет:
    - Определение базовых интентов (приветствия, вопросы и т.д.)
    - Определение специализированных интентов (MCP, YouTube)
    - Определение социальных медиа
    - Логику уточнения намерений
    """
    
    def __init__(self):
        """Инициализация с загрузкой всех паттернов"""
        self._init_patterns()
        self._init_social_media_patterns()
        self._init_specialized_patterns()
        logger.info("✅ UnifiedIntentService инициализирован")
        
    def _init_patterns(self):
        """Инициализация базовых паттернов"""
        self.patterns = {
            UnifiedIntentType.GREETING: [
                r'\b(привет|здравствуй|добрый день|добрый вечер|доброе утро|хай|hello|hi)\b',
                r'\b(приветствую|салют|здорово)\b'
            ],
            UnifiedIntentType.FAREWELL: [
                r'\b(пока|до свидания|прощай|увидимся|до встречи|bye|goodbye)\b',
                r'\b(спокойной ночи|доброй ночи)\b'
            ],
            UnifiedIntentType.HELP: [
                r'\b(помоги|помощь|help|что умеешь|что можешь|как пользоваться)\b',
                r'\b(инструкция|руководство|обучение|научи)\b'
            ],
            UnifiedIntentType.GRATITUDE: [
                r'\b(спасибо|благодарю|thanks|thank you|спс)\b',
                r'\b(признателен|благодарен)\b'
            ],
            UnifiedIntentType.COMPLAINT: [
                r'\b(не работает|сломалось|ошибка|проблема|баг|bug)\b',
                r'\b(плохо|ужасно|отвратительно|не нравится)\b'
            ]
        }
        
    def _init_social_media_patterns(self):
        """Инициализация паттернов социальных медиа"""
        self.url_patterns = {
            'youtube': [
                r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
                r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+'
            ],
            'instagram': [
                r'(?:https?://)?(?:www\.)?instagram\.com/[\w.]+',
                r'(?:https?://)?(?:www\.)?instagram\.com/p/[\w-]+',
                r'(?:https?://)?(?:www\.)?instagram\.com/reel/[\w-]+'
            ],
            'tiktok': [
                r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.]+/video/\d+',
                r'(?:https?://)?vm\.tiktok\.com/[\w-]+'
            ]
        }
        
        self.social_keywords = {
            'youtube': [
                'youtube', 'ютуб', 'видео', 'ролик', 'канал', 'подписчик',
                'просмотр', 'лайк', 'дизлайк', 'комментарий', 'субтитры'
            ],
            'instagram': [
                'instagram', 'инстаграм', 'инста', 'пост', 'сторис', 'stories',
                'рилс', 'reels', 'фото', 'подписчик', 'лайк'
            ],
            'tiktok': [
                'tiktok', 'тикток', 'тик ток', 'короткое видео', 'челлендж',
                'challenge', 'тренд', 'trend'
            ]
        }
        
    def _init_specialized_patterns(self):
        """Инициализация специализированных паттернов"""
        self.specialized_patterns = {
            UnifiedIntentType.MCP_COMMAND: [
                r"(покажи|показать|список|list|get|получить).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"(какие|что за|проверь).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"(статус|состояние|status).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"/mcp\s+\w+",
                r"/db\s+.+",
                r"выполни.*(mcp|команду)"
            ],
            UnifiedIntentType.YOUTUBE_ANALYSIS: [
                r"(проанализируй|анализ|посмотри|изучи).*(youtube|ютуб|видео)",
                r"(субтитры|subtitles|транскрипц).*(видео|youtube)",
                r"(получи|извлеки|достань).*(субтитры|текст).*(видео|youtube)",
                r"(статистика|просмотры|лайки).*(видео|youtube|ютуб)"
            ]
        }
        
    @measure_time
    async def detect(self, message: Message) -> Dict[str, Any]:
        """
        Определяет намерение сообщения
        
        Args:
            message: Сообщение для анализа
            
        Returns:
            Словарь с типом намерения, уверенностью и метаданными
        """
        text = message.text
        if not text:
            return self._create_intent_result(UnifiedIntentType.UNKNOWN)
            
        text_lower = text.lower()
        
        # 1. Проверяем команды
        if message.is_command:
            command, args = message.get_command()
            return self._create_intent_result(
                UnifiedIntentType.COMMAND,
                metadata={
                    "command": command,
                    "args": args
                }
            )
            
        # 2. Проверяем URL социальных медиа
        url_intent = self._detect_social_media_url(text)
        if url_intent:
            return url_intent
            
        # 3. Проверяем специализированные паттерны (MCP, YouTube)
        specialized_intent = self._detect_specialized_intent(text_lower)
        if specialized_intent:
            return specialized_intent
            
        # 4. Проверяем базовые паттерны
        for intent_type, patterns in self.patterns.items():
            if self._matches_patterns(text_lower, patterns):
                return self._create_intent_result(intent_type)
                
        # 5. Проверяем упоминания социальных медиа
        social_intent = self._detect_social_media_keywords(text_lower)
        if social_intent:
            return social_intent
            
        # 6. Проверяем, является ли это вопросом
        if self._is_question(text):
            return self._create_intent_result(UnifiedIntentType.QUESTION)
            
        # 7. По умолчанию - обычный чат
        return self._create_intent_result(UnifiedIntentType.GENERAL_CHAT, confidence=0.5)
        
    def classify_intent(self, text: str) -> Tuple[UnifiedIntentType, float, Dict[str, Any]]:
        """
        Альтернативный метод для совместимости с IntentClassifier
        
        Args:
            text: Текст для классификации
            
        Returns:
            Кортеж (тип намерения, уверенность, метаданные)
        """
        # Создаем временное сообщение для анализа
        from ..core.interfaces import User, UserRole
        temp_message = Message(
            id=0,
            user=User(id=0, role=UserRole.USER),
            chat_id=0,
            text=text,
            type="text",
            timestamp=datetime.now()
        )
        
        # Используем async метод синхронно
        import asyncio
        result = asyncio.create_task(self.detect(temp_message))
        
        # Извлекаем результаты
        intent_type = UnifiedIntentType(result.get("type", UnifiedIntentType.UNKNOWN))
        confidence = result.get("confidence", 0.0)
        metadata = result.get("metadata", {})
        
        return intent_type, confidence, metadata
        
    def _matches_patterns(self, text: str, patterns: List[str]) -> bool:
        """Проверяет соответствие текста паттернам"""
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
        
    def _detect_social_media_url(self, text: str) -> Optional[Dict[str, Any]]:
        """Определяет URL социальных медиа"""
        for platform, patterns in self.url_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    url = match.group(0)
                    
                    if platform == 'youtube':
                        video_id = self._extract_youtube_video_id(url)
                        return self._create_intent_result(
                            UnifiedIntentType.YOUTUBE_URL,
                            metadata={
                                "platform": platform,
                                "url": url,
                                "video_id": video_id
                            }
                        )
                        
                    return self._create_intent_result(
                        UnifiedIntentType.SOCIAL_MEDIA,
                        metadata={
                            "platform": platform,
                            "url": url
                        }
                    )
        return None
        
    def _detect_specialized_intent(self, text: str) -> Optional[Dict[str, Any]]:
        """Определяет специализированные намерения"""
        for intent_type, patterns in self.specialized_patterns.items():
            if self._matches_patterns(text, patterns):
                metadata = {"specialized": True}
                
                # Добавляем специфичные метаданные
                if intent_type == UnifiedIntentType.YOUTUBE_ANALYSIS:
                    # Проверяем наличие URL
                    url_match = re.search(r'https?://\S+', text)
                    if url_match:
                        metadata["has_url"] = True
                        metadata["url"] = url_match.group(0)
                        
                return self._create_intent_result(intent_type, confidence=0.85, metadata=metadata)
                
        return None
        
    def _detect_social_media_keywords(self, text: str) -> Optional[Dict[str, Any]]:
        """Определяет упоминания социальных медиа по ключевым словам"""
        scores = {}
        
        for platform, keywords in self.social_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    matched_keywords.append(keyword)
                    
            if score > 0:
                scores[platform] = {
                    "score": score,
                    "keywords": matched_keywords
                }
                
        if scores:
            best_platform = max(scores.keys(), key=lambda p: scores[p]["score"])
            
            return self._create_intent_result(
                UnifiedIntentType.SOCIAL_MEDIA,
                confidence=min(scores[best_platform]["score"] / 3, 0.9),
                metadata={
                    "platform": best_platform,
                    "matched_keywords": scores[best_platform]["keywords"],
                    "all_detected": list(scores.keys())
                }
            )
            
        return None
        
    def _is_question(self, text: str) -> bool:
        """Определяет, является ли текст вопросом"""
        if text.strip().endswith('?'):
            return True
            
        question_words = [
            'что', 'кто', 'где', 'когда', 'почему', 'зачем', 'как',
            'какой', 'какая', 'какое', 'какие', 'сколько', 'куда',
            'откуда', 'чей', 'чья', 'чье', 'чьи'
        ]
        
        text_lower = text.lower()
        for word in question_words:
            if text_lower.startswith(word + ' ') or f' {word} ' in text_lower:
                return True
                
        return False
        
    def _extract_youtube_video_id(self, url: str) -> Optional[str]:
        """Извлекает ID видео из YouTube URL"""
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed/)([0-9A-Za-z_-]{11})',
            r'(?:watch\?v=)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None
        
    def _create_intent_result(
        self,
        intent_type: UnifiedIntentType,
        confidence: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Создает результат определения намерения"""
        return {
            "type": intent_type.value,
            "confidence": confidence,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
    def needs_clarification(self, intent_type: UnifiedIntentType, confidence: float, text: str) -> bool:
        """
        Определяет, нужно ли уточнение намерения
        
        Args:
            intent_type: Определенный тип намерения
            confidence: Уверенность в определении
            text: Исходный текст сообщения
            
        Returns:
            True если нужно уточнение
        """
        # Команды не требуют уточнения
        if text.startswith('/'):
            return False
            
        # Низкая уверенность
        if confidence < 0.5:
            return True
            
        # Неоднозначные запросы
        if any(word in text.lower() for word in ['или', 'либо', 'не знаю', 'не уверен']):
            return True
            
        # YouTube без ссылки
        if intent_type == UnifiedIntentType.YOUTUBE_ANALYSIS and not re.search(r'https?://\S+', text):
            return True
            
        return False


# Глобальный экземпляр сервиса
unified_intent_service = UnifiedIntentService()