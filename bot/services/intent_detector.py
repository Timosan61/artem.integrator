"""
Детектор намерений пользователя

Определяет, что хочет сделать пользователь на основе его сообщения
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime

from ..core.interfaces import IIntentDetector, Message
from ..core.utils import TextUtils
from ..core.decorators import measure_time


logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Типы намерений"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    HELP = "help"
    SOCIAL_MEDIA = "social_media"
    YOUTUBE_URL = "youtube_url"
    QUESTION = "question"
    COMMAND = "command"
    GRATITUDE = "gratitude"
    COMPLAINT = "complaint"
    UNKNOWN = "unknown"


class SocialMediaPlatform(str, Enum):
    """Платформы социальных медиа"""
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    UNKNOWN = "unknown"


class IntentDetector(IIntentDetector):
    """Детектор намерений на основе правил и паттернов"""
    
    def __init__(self):
        """Инициализация детектора"""
        # Паттерны для приветствий
        self.greeting_patterns = [
            r'\b(привет|здравствуй|добрый день|добрый вечер|доброе утро|хай|hello|hi)\b',
            r'\b(приветствую|салют|здорово)\b'
        ]
        
        # Паттерны для прощаний
        self.farewell_patterns = [
            r'\b(пока|до свидания|прощай|увидимся|до встречи|bye|goodbye)\b',
            r'\b(спокойной ночи|доброй ночи)\b'
        ]
        
        # Паттерны для помощи
        self.help_patterns = [
            r'\b(помоги|помощь|help|что умеешь|что можешь|как пользоваться)\b',
            r'\b(инструкция|руководство|обучение|научи)\b'
        ]
        
        # Паттерны для благодарности
        self.gratitude_patterns = [
            r'\b(спасибо|благодарю|thanks|thank you|спс)\b',
            r'\b(признателен|благодарен)\b'
        ]
        
        # Паттерны для жалоб
        self.complaint_patterns = [
            r'\b(не работает|сломалось|ошибка|проблема|баг|bug)\b',
            r'\b(плохо|ужасно|отвратительно|не нравится)\b'
        ]
        
        # Ключевые слова для социальных медиа
        self.social_media_keywords = {
            SocialMediaPlatform.YOUTUBE: [
                'youtube', 'ютуб', 'видео', 'ролик', 'канал', 'подписчик',
                'просмотр', 'лайк', 'дизлайк', 'комментарий', 'трек', 'клип',
                'стрим', 'stream', 'влог', 'vlog', 'контент'
            ],
            SocialMediaPlatform.INSTAGRAM: [
                'instagram', 'инстаграм', 'инста', 'пост', 'сторис', 'stories',
                'рилс', 'reels', 'фото', 'подписчик', 'лайк', 'хештег', 'hashtag'
            ],
            SocialMediaPlatform.TIKTOK: [
                'tiktok', 'тикток', 'тик ток', 'короткое видео', 'челлендж',
                'challenge', 'тренд', 'trend', 'дуэт', 'duet'
            ]
        }
        
        # Паттерны URL для разных платформ
        self.url_patterns = {
            SocialMediaPlatform.YOUTUBE: [
                r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
                r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/channel/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/c/[\w-]+',
                r'(?:https?://)?(?:www\.)?youtube\.com/@[\w-]+'
            ],
            SocialMediaPlatform.INSTAGRAM: [
                r'(?:https?://)?(?:www\.)?instagram\.com/[\w.]+',
                r'(?:https?://)?(?:www\.)?instagram\.com/p/[\w-]+',
                r'(?:https?://)?(?:www\.)?instagram\.com/reel/[\w-]+'
            ],
            SocialMediaPlatform.TIKTOK: [
                r'(?:https?://)?(?:www\.)?tiktok\.com/@[\w.]+/video/\d+',
                r'(?:https?://)?vm\.tiktok\.com/[\w-]+'
            ]
        }
    
    @measure_time
    async def detect(self, message: Message) -> Dict[str, Any]:
        """Определяет намерение сообщения"""
        text = message.text
        if not text:
            return self._create_intent_result(IntentType.UNKNOWN)
        
        text_lower = text.lower()
        
        # Проверяем команды
        if message.is_command:
            command, args = message.get_command()
            return self._create_intent_result(
                IntentType.COMMAND,
                metadata={
                    "command": command,
                    "args": args
                }
            )
        
        # Проверяем URL социальных медиа
        url_intent = self._detect_social_media_url(text)
        if url_intent:
            return url_intent
        
        # Проверяем приветствия
        if self._matches_patterns(text_lower, self.greeting_patterns):
            return self._create_intent_result(IntentType.GREETING)
        
        # Проверяем прощания
        if self._matches_patterns(text_lower, self.farewell_patterns):
            return self._create_intent_result(IntentType.FAREWELL)
        
        # Проверяем просьбы о помощи
        if self._matches_patterns(text_lower, self.help_patterns):
            return self._create_intent_result(IntentType.HELP)
        
        # Проверяем благодарность
        if self._matches_patterns(text_lower, self.gratitude_patterns):
            return self._create_intent_result(IntentType.GRATITUDE)
        
        # Проверяем жалобы
        if self._matches_patterns(text_lower, self.complaint_patterns):
            return self._create_intent_result(IntentType.COMPLAINT)
        
        # Проверяем упоминания социальных медиа
        social_media_intent = self._detect_social_media_keywords(text_lower)
        if social_media_intent:
            return social_media_intent
        
        # Проверяем, является ли это вопросом
        if self._is_question(text):
            return self._create_intent_result(IntentType.QUESTION)
        
        # Неизвестное намерение
        return self._create_intent_result(IntentType.UNKNOWN)
    
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
                    
                    # Для YouTube извлекаем ID видео
                    if platform == SocialMediaPlatform.YOUTUBE:
                        video_id = self._extract_youtube_video_id(url)
                        return self._create_intent_result(
                            IntentType.YOUTUBE_URL,
                            metadata={
                                "platform": platform.value,
                                "url": url,
                                "video_id": video_id
                            }
                        )
                    
                    return self._create_intent_result(
                        IntentType.SOCIAL_MEDIA,
                        metadata={
                            "platform": platform.value,
                            "url": url
                        }
                    )
        
        return None
    
    def _detect_social_media_keywords(self, text: str) -> Optional[Dict[str, Any]]:
        """Определяет упоминания социальных медиа по ключевым словам"""
        detected_platforms = []
        scores = {}
        
        for platform, keywords in self.social_media_keywords.items():
            score = 0
            matched_keywords = []
            
            for keyword in keywords:
                if keyword in text:
                    score += 1
                    matched_keywords.append(keyword)
            
            if score > 0:
                detected_platforms.append(platform)
                scores[platform] = {
                    "score": score,
                    "keywords": matched_keywords
                }
        
        if detected_platforms:
            # Выбираем платформу с наибольшим score
            best_platform = max(detected_platforms, key=lambda p: scores[p]["score"])
            
            return self._create_intent_result(
                IntentType.SOCIAL_MEDIA,
                metadata={
                    "platform": best_platform.value,
                    "confidence": scores[best_platform]["score"] / len(self.social_media_keywords[best_platform]),
                    "matched_keywords": scores[best_platform]["keywords"],
                    "all_detected": [p.value for p in detected_platforms]
                }
            )
        
        return None
    
    def _is_question(self, text: str) -> bool:
        """Определяет, является ли текст вопросом"""
        # Проверяем вопросительный знак
        if text.strip().endswith('?'):
            return True
        
        # Проверяем вопросительные слова
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
        intent_type: IntentType,
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


class AIIntentDetector(IIntentDetector):
    """Детектор намерений на основе AI (для сложных случаев)"""
    
    def __init__(self, ai_client):
        """
        Args:
            ai_client: Клиент AI для анализа намерений
        """
        self.ai_client = ai_client
        self.rule_based_detector = IntentDetector()
    
    async def detect(self, message: Message) -> Dict[str, Any]:
        """Определяет намерение с помощью AI"""
        # Сначала пробуем rule-based детектор
        rule_based_result = await self.rule_based_detector.detect(message)
        
        # Если уверенность высокая или это команда/URL, возвращаем результат
        if (rule_based_result["confidence"] > 0.8 or 
            rule_based_result["type"] in [IntentType.COMMAND, IntentType.YOUTUBE_URL]):
            return rule_based_result
        
        # Для неопределенных случаев используем AI
        try:
            prompt = f"""Определи намерение пользователя в сообщении.

Сообщение: "{message.text}"

Возможные намерения:
- greeting: приветствие
- farewell: прощание
- help: просьба о помощи
- social_media: упоминание социальных медиа
- question: вопрос
- gratitude: благодарность
- complaint: жалоба
- unknown: неопределенное

Ответь в формате JSON:
{{
    "intent": "название_намерения",
    "confidence": 0.0-1.0,
    "reason": "краткое объяснение"
}}"""

            # Здесь должен быть вызов AI
            # response = await self.ai_client.generate(prompt)
            # Пока возвращаем rule-based результат
            return rule_based_result
            
        except Exception as e:
            logger.error(f"Ошибка AI детектора намерений: {e}")
            return rule_based_result