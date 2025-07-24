"""
YouTube Analyzer Tool - анализ YouTube видео через YouTube Data API
"""
import os
import re
import json
from typing import Dict, Any, Type, Optional, List
from urllib.parse import urlparse, parse_qs
import aiohttp
from pathlib import Path

from .base import BaseTool, ToolMetadata
from ..core.models import BaseToolParams, ToolResponse, YouTubeAnalysisParams, ToolType


class YouTubeAnalyzerTool(BaseTool):
    """Инструмент для анализа YouTube видео"""
    
    @property
    def metadata(self) -> ToolMetadata:
        """Свойство для совместимости с ToolRegistry"""
        return self.get_metadata()
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            self.logger.warning("⚠️ YouTube API key не найден, будет использоваться эмуляция")
        
        # API endpoints
        self.video_api_url = "https://www.googleapis.com/youtube/v3/videos"
        self.captions_api_url = "https://www.googleapis.com/youtube/v3/captions"
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="youtube_analyzer",
            description="Анализирует YouTube видео: извлекает информацию, субтитры и метаданные",
            version="1.0.0",
            requires_confirmation=False,
            estimated_time="5-15 секунд"
        )
    
    def get_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "analyze_youtube_video",
                "description": self.metadata.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL YouTube видео для анализа"
                        },
                        "user_id": {
                            "type": "string",
                            "description": "ID пользователя"
                        },
                        "extract_subtitles": {
                            "type": "boolean",
                            "description": "Извлечь субтитры видео",
                            "default": True
                        },
                        "subtitle_language": {
                            "type": "string",
                            "description": "Язык субтитров (ru, en, auto)",
                            "default": "ru"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Включить метаданные видео",
                            "default": True
                        }
                    },
                    "required": ["url", "user_id"]
                }
            }
        }
    
    def get_params_model(self) -> Type[BaseToolParams]:
        return YouTubeAnalysisParams
    
    async def execute(self, params: YouTubeAnalysisParams) -> ToolResponse:
        """Анализирует YouTube видео"""
        try:
            # Извлекаем video ID из URL
            video_id = self._extract_video_id(params.url)
            if not video_id:
                return ToolResponse(
                    success=False,
                    error="Не удалось извлечь ID видео из URL",
                    metadata={"tool_type": ToolType.YOUTUBE_ANALYZER}
                )
            
            self.logger.info(f"🎥 Анализ YouTube видео: {video_id}")
            
            if self.api_key:
                # Реальный API вызов
                result = await self._analyze_with_api(video_id, params)
            else:
                # Эмуляция для тестирования
                result = await self._emulate_analysis(video_id, params)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа YouTube видео: {e}", exc_info=True)
            return ToolResponse(
                success=False,
                error=f"Ошибка анализа видео: {str(e)}",
                metadata={"tool_type": ToolType.YOUTUBE_ANALYZER}
            )
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Извлекает ID видео из различных форматов YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Попробуем parse_qs для сложных URL
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
            query = parse_qs(parsed.query)
            if 'v' in query:
                return query['v'][0]
        
        return None
    
    async def _analyze_with_api(self, video_id: str, params: YouTubeAnalysisParams) -> ToolResponse:
        """Реальный анализ через YouTube Data API"""
        async with aiohttp.ClientSession() as session:
            # Получаем информацию о видео
            video_data = await self._fetch_video_data(session, video_id)
            
            if not video_data:
                return ToolResponse(
                    success=False,
                    error="Не удалось получить данные о видео",
                    metadata={"tool_type": ToolType.YOUTUBE_ANALYZER}
                )
            
            result = {
                "video_id": video_id,
                "url": f"https://youtube.com/watch?v={video_id}"
            }
            
            # Добавляем метаданные
            if params.include_metadata and video_data.get("items"):
                item = video_data["items"][0]
                snippet = item.get("snippet", {})
                statistics = item.get("statistics", {})
                content_details = item.get("contentDetails", {})
                
                result["metadata"] = {
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "channel": snippet.get("channelTitle"),
                    "published_at": snippet.get("publishedAt"),
                    "duration": self._parse_duration(content_details.get("duration")),
                    "tags": snippet.get("tags", []),
                    "category": snippet.get("categoryId"),
                    "statistics": {
                        "views": int(statistics.get("viewCount", 0)),
                        "likes": int(statistics.get("likeCount", 0)),
                        "comments": int(statistics.get("commentCount", 0))
                    }
                }
            
            # Получаем субтитры
            if params.extract_subtitles:
                subtitles = await self._fetch_subtitles(session, video_id, params.subtitle_language)
                if subtitles:
                    result["subtitles"] = subtitles
                else:
                    result["subtitles"] = {"error": "Субтитры недоступны для этого видео"}
            
            return ToolResponse(
                success=True,
                data=result,
                metadata={
                    "tool_type": ToolType.YOUTUBE_ANALYZER,
                    "video_id": video_id,
                    "has_subtitles": bool(result.get("subtitles") and not result["subtitles"].get("error"))
                }
            )
    
    async def _fetch_video_data(self, session: aiohttp.ClientSession, video_id: str) -> Optional[Dict]:
        """Получает данные о видео через YouTube API"""
        params = {
            "part": "snippet,statistics,contentDetails",
            "id": video_id,
            "key": self.api_key
        }
        
        try:
            async with session.get(self.video_api_url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    self.logger.error(f"YouTube API error: {response.status}")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching video data: {e}")
            return None
    
    async def _fetch_subtitles(self, session: aiohttp.ClientSession, video_id: str, language: str) -> Optional[Dict]:
        """Получает субтитры видео"""
        # Сначала получаем список доступных субтитров
        params = {
            "part": "snippet",
            "videoId": video_id,
            "key": self.api_key
        }
        
        try:
            async with session.get(self.captions_api_url, params=params) as response:
                if response.status == 200:
                    captions_data = await response.json()
                    
                    # Ищем субтитры на нужном языке
                    captions = captions_data.get("items", [])
                    
                    # Приоритеты: запрошенный язык > русский > английский > первый доступный
                    language_priority = [language, "ru", "en"]
                    
                    for lang in language_priority:
                        for caption in captions:
                            if caption["snippet"]["language"] == lang:
                                # Здесь должен быть код для загрузки текста субтитров
                                # Но это требует OAuth2, поэтому возвращаем информацию о доступности
                                return {
                                    "available": True,
                                    "language": lang,
                                    "name": caption["snippet"]["name"],
                                    "is_auto_generated": caption["snippet"]["trackKind"] == "asr",
                                    "note": "Для получения полного текста субтитров требуется OAuth авторизация"
                                }
                    
                    # Если есть хоть какие-то субтитры
                    if captions:
                        first = captions[0]
                        return {
                            "available": True,
                            "language": first["snippet"]["language"],
                            "name": first["snippet"]["name"],
                            "is_auto_generated": first["snippet"]["trackKind"] == "asr",
                            "note": "Субтитры на запрошенном языке не найдены"
                        }
                    
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching subtitles: {e}")
            return None
    
    def _parse_duration(self, duration: str) -> str:
        """Парсит ISO 8601 duration в читаемый формат"""
        if not duration:
            return "Неизвестно"
        
        # ISO 8601 duration format: PT#H#M#S
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration)
        
        if match:
            hours, minutes, seconds = match.groups()
            parts = []
            
            if hours:
                parts.append(f"{hours}ч")
            if minutes:
                parts.append(f"{minutes}м")
            if seconds:
                parts.append(f"{seconds}с")
            
            return " ".join(parts) if parts else "0с"
        
        return duration
    
    async def _emulate_analysis(self, video_id: str, params: YouTubeAnalysisParams) -> ToolResponse:
        """Эмулирует анализ видео для тестирования"""
        emulated_data = {
            "dQw4w9WgXcQ": {
                "title": "Rick Astley - Never Gonna Give You Up",
                "channel": "Rick Astley",
                "duration": "3м 33с",
                "views": 1400000000,
                "description": "The official video for 'Never Gonna Give You Up' by Rick Astley",
                "subtitles": "Never gonna give you up\nNever gonna let you down\nNever gonna run around and desert you..."
            },
            "jNQXAC9IVRw": {
                "title": "Me at the zoo",
                "channel": "jawed",
                "duration": "19с",
                "views": 300000000,
                "description": "The first video on YouTube",
                "subtitles": "All right, so here we are in front of the elephants..."
            }
        }
        
        # Используем дефолтные данные если video_id не в эмулированных
        video_info = emulated_data.get(video_id, {
            "title": f"Видео {video_id}",
            "channel": "Test Channel",
            "duration": "5м 30с",
            "views": 1000000,
            "description": "Это эмулированное описание видео для тестирования",
            "subtitles": "Это эмулированные субтитры для тестирования..."
        })
        
        result = {
            "video_id": video_id,
            "url": f"https://youtube.com/watch?v={video_id}"
        }
        
        if params.include_metadata:
            result["metadata"] = {
                "title": video_info["title"],
                "description": video_info["description"],
                "channel": video_info["channel"],
                "published_at": "2024-01-01T00:00:00Z",
                "duration": video_info["duration"],
                "tags": ["test", "emulation"],
                "statistics": {
                    "views": video_info["views"],
                    "likes": int(video_info["views"] * 0.05),
                    "comments": int(video_info["views"] * 0.001)
                }
            }
        
        if params.extract_subtitles:
            result["subtitles"] = {
                "available": True,
                "language": params.subtitle_language,
                "text": video_info["subtitles"],
                "is_auto_generated": False,
                "emulated": True
            }
        
        return ToolResponse(
            success=True,
            data=result,
            metadata={
                "tool_type": ToolType.YOUTUBE_ANALYZER,
                "video_id": video_id,
                "emulated": True,
                "has_subtitles": True
            }
        )
    
    def get_confirmation_message(self, params: YouTubeAnalysisParams) -> str:
        """Возвращает сообщение для подтверждения (не используется, так как не требует подтверждения)"""
        return f"Анализ YouTube видео: {params.url}"