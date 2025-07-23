"""
Intent Classifier - классификатор намерений пользователя
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import yaml
from enum import Enum

from ..core.models import ToolType

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    """Типы намерений пользователя"""
    MCP_COMMAND = "mcp_command"
    IMAGE_GENERATION = "image_generation"
    VIDEO_ANALYSIS = "video_analysis"
    GENERAL_CHAT = "general_chat"
    CLARIFICATION_NEEDED = "clarification_needed"


class IntentPattern:
    """Паттерн для определения намерения"""
    
    def __init__(self, intent: Intent, patterns: List[str], confidence: float = 0.8):
        self.intent = intent
        self.patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
        self.confidence = confidence


class IntentClassifier:
    """Классификатор намерений пользователя"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.patterns: List[IntentPattern] = []
        self.tool_keywords: Dict[ToolType, List[str]] = {}
        
        # Загружаем базовые паттерны
        self._load_default_patterns()
        
        # Загружаем паттерны из конфигурации если указана
        if config_path:
            self.load_patterns_from_yaml(config_path)
        
        logger.info("🧠 IntentClassifier инициализирован")
    
    def _load_default_patterns(self):
        """Загружает стандартные паттерны"""
        # MCP команды
        self.patterns.append(IntentPattern(
            Intent.MCP_COMMAND,
            [
                r"(покажи|показать|список|list|get|получить).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"(какие|что за|проверь).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"(статус|состояние|status).*(приложен|app|база|базы|данн|database|db|деплой|deploy)",
                r"/mcp\s+\w+",
                r"/db\s+.+",
                r"выполни.*(mcp|команду)"
            ],
            confidence=0.85
        ))
        
        # Генерация изображений
        self.patterns.append(IntentPattern(
            Intent.IMAGE_GENERATION,
            [
                r"(нарисуй|сгенерируй|создай|сделай).*(картин|изображен|рисун|фото|image|picture|арт|котик|собак|животн|пейзаж|портрет)",
                r"(нарисуй|сгенерируй|создай)\s+\w+",  # нарисуй котика, создай дизайн и т.д.
                r"(картин|изображен|рисун|фото).*(с|где|на котор)",
                r"dall-?e",
                r"визуализируй",
                r"проиллюстрируй"
            ],
            confidence=0.9
        ))
        
        # Анализ видео
        self.patterns.append(IntentPattern(
            Intent.VIDEO_ANALYSIS,
            [
                r"(проанализируй|анализ|посмотри|изучи).*(видео|ролик|рилс|reels|video)",
                r"(что|о чем|про что).*(видео|ролик|рилс)",
                r"(видео|ролик|рилс).*(анализ|проанализ|разбор)",
                r"(скачай|загрузи).*(видео|ролик).*анализ",
                r"vision.*видео"
            ],
            confidence=0.85
        ))
        
        # Ключевые слова для инструментов
        self.tool_keywords = {
            ToolType.MCP: [
                "приложение", "приложения", "app", "apps",
                "база", "базы", "данных", "database", "db",
                "деплой", "деплоймент", "deploy", "deployment",
                "сервер", "server", "инфраструктура"
            ],
            ToolType.IMAGE_GENERATOR: [
                "картинка", "изображение", "рисунок", "фото",
                "нарисуй", "сгенерируй", "создай изображение",
                "dall-e", "dalle", "визуализация", "иллюстрация",
                "арт", "дизайн", "art", "design", "картинку"
            ],
            ToolType.VISION_ANALYZER: [
                "видео", "ролик", "рилс", "reels",
                "проанализируй видео", "анализ видео",
                "vision", "покадровый", "кадры"
            ]
        }
    
    def load_patterns_from_yaml(self, config_path: str) -> bool:
        """
        Загружает паттерны из YAML файла
        
        Args:
            config_path: Путь к YAML файлу
            
        Returns:
            True если успешно загружено
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            patterns_config = config.get('intent_patterns', [])
            
            for pattern_config in patterns_config:
                intent = Intent(pattern_config['intent'])
                patterns = pattern_config['patterns']
                confidence = pattern_config.get('confidence', 0.8)
                
                self.patterns.append(IntentPattern(intent, patterns, confidence))
            
            # Загружаем дополнительные ключевые слова
            keywords_config = config.get('tool_keywords', {})
            for tool_type_str, keywords in keywords_config.items():
                try:
                    tool_type = ToolType(tool_type_str)
                    if tool_type not in self.tool_keywords:
                        self.tool_keywords[tool_type] = []
                    self.tool_keywords[tool_type].extend(keywords)
                except ValueError:
                    logger.warning(f"Неизвестный тип инструмента в конфигурации: {tool_type_str}")
            
            logger.info(f"📚 Загружено {len(patterns_config)} паттернов из {config_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки паттернов из {config_path}: {e}")
            return False
    
    def classify(self, user_message: str) -> Tuple[Intent, float, Dict[str, Any]]:
        """
        Классифицирует намерение пользователя
        
        Args:
            user_message: Сообщение пользователя
            
        Returns:
            Кортеж (Intent, confidence, metadata)
        """
        user_message_lower = user_message.lower()
        best_intent = Intent.GENERAL_CHAT
        best_confidence = 0.0
        metadata = {}
        
        # Проверяем паттерны
        for pattern_group in self.patterns:
            for pattern in pattern_group.patterns:
                if pattern.search(user_message):
                    if pattern_group.confidence > best_confidence:
                        best_intent = pattern_group.intent
                        best_confidence = pattern_group.confidence
                        break
        
        # Если намерение не определено точно, анализируем ключевые слова
        if best_confidence < 0.7:
            keyword_scores = self._analyze_keywords(user_message_lower)
            if keyword_scores:
                # Выбираем инструмент с наивысшим счетом
                best_tool, score = max(keyword_scores.items(), key=lambda x: x[1])
                
                # Мапинг инструментов на намерения
                tool_to_intent = {
                    ToolType.MCP: Intent.MCP_COMMAND,
                    ToolType.IMAGE_GENERATOR: Intent.IMAGE_GENERATION,
                    ToolType.VISION_ANALYZER: Intent.VIDEO_ANALYSIS
                }
                
                if score > 0.2:  # Снизил порог для ключевых слов
                    best_intent = tool_to_intent.get(best_tool, Intent.GENERAL_CHAT)
                    best_confidence = min(score * 1.5, 0.75)  # Увеличиваем confidence
                    metadata['keyword_based'] = True
                    metadata['suggested_tool'] = best_tool
        
        # Проверяем нужно ли уточнение (только если это не обычный чат)
        if best_intent != Intent.GENERAL_CHAT and self._needs_clarification(user_message, best_intent, best_confidence):
            metadata['original_intent'] = best_intent
            metadata['original_confidence'] = best_confidence
            best_intent = Intent.CLARIFICATION_NEEDED
            best_confidence = 0.9
        
        # Добавляем метаданные
        metadata.update({
            'message_length': len(user_message),
            'has_url': bool(re.search(r'https?://\S+', user_message)),
            'has_command': user_message.startswith('/'),
            'detected_tools': self._detect_potential_tools(user_message_lower),
            'message_text': user_message  # Добавляем для get_clarification_options
        })
        
        logger.info(f"🎯 Классифицировано: {best_intent} (уверенность: {best_confidence:.2f})")
        return best_intent, best_confidence, metadata
    
    def _analyze_keywords(self, message: str) -> Dict[ToolType, float]:
        """
        Анализирует ключевые слова для определения подходящего инструмента
        
        Args:
            message: Сообщение в нижнем регистре
            
        Returns:
            Словарь {ToolType: score}
        """
        scores = {}
        
        for tool_type, keywords in self.tool_keywords.items():
            score = 0.0
            matches = 0
            
            for keyword in keywords:
                # Используем word boundaries для точного соответствия
                if re.search(r'\b' + re.escape(keyword.lower()) + r'\b', message):
                    matches += 1
                    # Увеличиваем вес для более специфичных ключевых слов
                    if len(keyword) > 5:
                        score += 0.3
                    else:
                        score += 0.15
            
            if matches > 0:
                # Нормализуем score по количеству совпадений
                scores[tool_type] = min(score, 1.0)
        
        return scores
    
    def _needs_clarification(self, message: str, intent: Intent, confidence: float) -> bool:
        """
        Определяет, нужно ли уточнение намерения
        
        Args:
            message: Сообщение пользователя
            intent: Определенное намерение
            confidence: Уверенность
            
        Returns:
            True если нужно уточнение
        """
        # Если это четкая команда, не нужно уточнение
        if message.startswith('/'):
            return False
            
        # Очень низкая уверенность - всегда нужно уточнение
        if confidence < 0.3:  # Снизил порог
            return True
        
        # Неоднозначные запросы
        ambiguous_patterns = [
            r"(или|либо)",  # Убрал "может" и "возможно" - они часто используются в обычных запросах
            r"(не знаю|не уверен)",
            r"\?.*\?"  # Несколько вопросов
        ]
        
        for pattern in ambiguous_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        
        # Для видео анализа - проверяем наличие ссылки
        if intent == Intent.VIDEO_ANALYSIS and not re.search(r'https?://\S+', message):
            return True
        
        return False
    
    def _detect_potential_tools(self, message: str) -> List[ToolType]:
        """
        Определяет потенциально подходящие инструменты
        
        Args:
            message: Сообщение в нижнем регистре
            
        Returns:
            Список подходящих инструментов
        """
        tools = []
        
        # Анализируем по ключевым словам
        keyword_scores = self._analyze_keywords(message)
        
        # Выбираем инструменты с score > 0.3
        for tool_type, score in keyword_scores.items():
            if score > 0.3:
                tools.append(tool_type)
        
        # Сортируем по релевантности
        tools.sort(key=lambda t: keyword_scores.get(t, 0), reverse=True)
        
        return tools
    
    def get_clarification_options(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Возвращает варианты для уточнения намерения
        
        Args:
            metadata: Метаданные классификации
            
        Returns:
            Список вариантов для пользователя
        """
        options = []
        detected_tools = metadata.get('detected_tools', [])
        
        # Мапинг инструментов на описания
        tool_descriptions = {
            ToolType.MCP: {
                'name': 'Управление инфраструктурой',
                'description': 'Просмотр приложений, баз данных, деплойментов',
                'icon': '🔧'
            },
            ToolType.IMAGE_GENERATOR: {
                'name': 'Генерация изображений',
                'description': 'Создание изображений по текстовому описанию',
                'icon': '🎨'
            },
            ToolType.VISION_ANALYZER: {
                'name': 'Анализ видео',
                'description': 'Анализ видео контента, извлечение информации',
                'icon': '📹'
            }
        }
        
        # Если нет detected_tools, попробуем получить из ключевых слов
        if not detected_tools:
            # Анализируем ключевые слова для получения потенциальных инструментов
            keyword_scores = self._analyze_keywords(metadata.get('message_text', '').lower())
            if keyword_scores:
                # Сортируем по score и берем топ 3
                sorted_tools = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
                detected_tools = [tool for tool, score in sorted_tools[:3] if score > 0.1]
        
        # Добавляем опции на основе обнаруженных инструментов
        for tool in detected_tools[:3]:  # Максимум 3 варианта
            if tool in tool_descriptions:
                desc = tool_descriptions[tool]
                options.append({
                    'tool': tool,
                    'name': desc['name'],
                    'description': desc['description'],
                    'icon': desc['icon']
                })
        
        # Добавляем опцию "просто поговорить" если есть другие варианты
        if options:
            options.append({
                'tool': None,
                'name': 'Обычный разговор',
                'description': 'Просто поговорить без использования специальных инструментов',
                'icon': '💬'
            })
        
        return options