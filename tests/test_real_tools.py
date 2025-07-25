"""
Тесты для реальных инструментов (YouTube)
Примечание: MCPTool удален в рамках упрощенной Simple Agent архитектуры
"""
import pytest
import asyncio
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Добавляем путь к корню проекта
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent.tools.youtube_tool import YouTubeAnalyzerTool
from agent.core.models import YouTubeAnalysisParams, ToolResponse


# Примечание: Тесты для MCPTool удалены, так как MCPTool был убран 
# в рамках упрощенной Simple Agent архитектуры. Теперь используется 
# прямой вызов через claude_code_direct функцию в IntelligentAgent.


class TestYouTubeAnalyzerTool:
    """Тесты для YouTube анализатора"""
    
    @pytest.fixture
    def youtube_tool(self):
        """Создает экземпляр YouTubeAnalyzerTool без API ключа"""
        return YouTubeAnalyzerTool(api_key=None)
    
    def test_video_id_extraction(self, youtube_tool):
        """Тест извлечения ID видео из различных URL"""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/watch?v=dQw4w9WgXcQ&feature=share", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("not a youtube url", None),
        ]
        
        for url, expected_id in test_cases:
            result = youtube_tool._extract_video_id(url)
            assert result == expected_id, f"Для URL {url} ожидался ID {expected_id}"
    
    def test_duration_parsing(self, youtube_tool):
        """Тест парсинга ISO 8601 duration"""
        test_cases = [
            ("PT3M33S", "3м 33с"),
            ("PT1H2M30S", "1ч 2м 30с"),
            ("PT45S", "45с"),
            ("PT1H", "1ч"),
            ("PT10M", "10м"),
            ("", "Неизвестно"),
        ]
        
        for iso_duration, expected in test_cases:
            result = youtube_tool._parse_duration(iso_duration)
            assert result == expected, f"Для {iso_duration} ожидалось {expected}"
    
    @pytest.mark.asyncio
    async def test_youtube_emulation_analysis(self, youtube_tool):
        """Тест эмулированного анализа YouTube видео"""
        params = YouTubeAnalysisParams(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            user_id="test_user",
            extract_subtitles=True,
            include_metadata=True
        )
        
        response = await youtube_tool.execute(params)
        
        assert response.success is True
        assert response.data is not None
        
        # Проверяем структуру ответа
        data = response.data
        assert data["video_id"] == "dQw4w9WgXcQ"
        assert "metadata" in data
        assert "subtitles" in data
        
        # Проверяем метаданные
        metadata = data["metadata"]
        assert "title" in metadata
        assert "channel" in metadata
        assert "statistics" in metadata
        
        # Проверяем субтитры
        subtitles = data["subtitles"]
        assert subtitles.get("available") is True
        # В реальном API у нас есть YouTube API ключ, поэтому возвращается реальный ответ
        # Проверяем структуру субтитров
        assert "language" in subtitles or "emulated" in subtitles
    
    @pytest.mark.asyncio
    async def test_youtube_invalid_url(self, youtube_tool):
        """Тест обработки невалидного URL"""
        params = YouTubeAnalysisParams(
            url="https://not-youtube.com/video",
            user_id="test_user"
        )
        
        response = await youtube_tool.execute(params)
        
        assert response.success is False
        assert "Не удалось извлечь ID видео" in response.error
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_youtube_api_call(self, mock_get):
        """Тест реального API вызова с моком"""
        # Создаем инструмент с API ключом
        youtube_tool = YouTubeAnalyzerTool(api_key="test_api_key")
        
        # Мокаем ответ API для информации о видео
        video_response = AsyncMock()
        video_response.status = 200
        video_response.json = AsyncMock(return_value={
            "items": [{
                "snippet": {
                    "title": "Test Video",
                    "description": "Test Description",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-01T00:00:00Z",
                    "tags": ["test", "video"],
                    "categoryId": "22"
                },
                "statistics": {
                    "viewCount": "1000000",
                    "likeCount": "50000",
                    "commentCount": "5000"
                },
                "contentDetails": {
                    "duration": "PT5M30S"
                }
            }]
        })
        
        # Мокаем ответ API для субтитров
        captions_response = AsyncMock()
        captions_response.status = 200
        captions_response.json = AsyncMock(return_value={
            "items": [{
                "snippet": {
                    "language": "ru",
                    "name": "Русский",
                    "trackKind": "standard"
                }
            }]
        })
        
        # Настраиваем мок для возврата разных ответов
        mock_get.return_value.__aenter__.side_effect = [video_response, captions_response]
        
        params = YouTubeAnalysisParams(
            url="https://www.youtube.com/watch?v=test123",
            user_id="test_user",
            extract_subtitles=True,
            include_metadata=True,
            subtitle_language="ru"
        )
        
        response = await youtube_tool.execute(params)
        
        assert response.success is True
        assert response.data["metadata"]["title"] == "Test Video"
        assert response.data["metadata"]["statistics"]["views"] == 1000000
        assert response.data["subtitles"]["available"] is True
        assert response.data["subtitles"]["language"] == "ru"


# Интеграционные тесты
class TestToolIntegration:
    """Интеграционные тесты для работы инструментов вместе"""
    
    @pytest.mark.asyncio
    async def test_youtube_tool_metadata(self):
        """Тест метаданных YouTube инструмента"""
        youtube_tool = YouTubeAnalyzerTool()
        
        # Проверяем метаданные YouTube
        youtube_meta = youtube_tool.get_metadata()
        assert youtube_meta.name == "youtube_analyzer"
        assert youtube_meta.requires_confirmation is False
    
    @pytest.mark.asyncio
    async def test_youtube_openai_schema(self):
        """Тест схемы YouTube для OpenAI"""
        youtube_tool = YouTubeAnalyzerTool()
        
        # Проверяем схему YouTube
        youtube_schema = youtube_tool.get_openai_schema()
        assert youtube_schema["type"] == "function"
        assert "analyze_youtube_video" in youtube_schema["function"]["name"]
        assert "url" in youtube_schema["function"]["parameters"]["properties"]
        assert "extract_subtitles" in youtube_schema["function"]["parameters"]["properties"]


if __name__ == "__main__":
    # Запускаем тесты
    pytest.main([__file__, "-v", "--tb=short"])