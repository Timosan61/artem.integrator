"""
Тесты для реальных инструментов (MCP и YouTube)
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

from agent.tools.mcp_tool import MCPTool
from agent.tools.youtube_tool import YouTubeAnalyzerTool
from agent.core.models import MCPCommandParams, YouTubeAnalysisParams, ToolResponse


class TestMCPTool:
    """Тесты для MCP инструмента"""
    
    @pytest.fixture
    def mcp_tool(self):
        """Создает экземпляр MCPTool"""
        return MCPTool()
    
    @pytest.mark.asyncio
    async def test_mcp_command_formatting(self, mcp_tool):
        """Тест форматирования MCP команд"""
        # Тестируем различные форматы команд
        test_cases = [
            ("list apps", "/mcp apps"),
            ("show databases", "/db SELECT datname FROM pg_database"),
            ("приложения", "/mcp apps"),
            ("базы данных", "/db SELECT datname FROM pg_database"),
            ("/mcp apps", "/mcp apps"),  # Уже отформатированная
            ("get deployments", "/mcp apps"),
        ]
        
        for input_cmd, expected in test_cases:
            result = mcp_tool._format_command(input_cmd)
            assert result == expected, f"Ожидалось {expected}, получено {result}"
    
    @pytest.mark.asyncio
    async def test_mcp_command_type_detection(self, mcp_tool):
        """Тест определения типа команды"""
        test_cases = [
            ("show apps", "applications"),
            ("list databases", "databases"),
            ("get deployments", "deployments"),
            ("базы данных", "databases"),
            ("random command", "general"),
        ]
        
        for command, expected_type in test_cases:
            result = mcp_tool._get_command_type(command)
            assert result == expected_type, f"Для команды '{command}' ожидался тип {expected_type}"
    
    @pytest.mark.asyncio
    async def test_mcp_emulation_response(self, mcp_tool):
        """Тест эмулированного ответа MCP"""
        params = MCPCommandParams(
            command="list apps",
            user_id="test_user"
        )
        
        response = await mcp_tool.execute(params)
        
        assert response.success is True
        assert response.data is not None
        mcp_response = response.data.get("mcp_response")
        assert mcp_response is not None
        # В зависимости от того, используется реальный сервис или эмуляция
        if isinstance(mcp_response, dict):
            assert "apps" in mcp_response
            assert response.metadata.get("emulated") is True
        elif isinstance(mcp_response, list):
            # Реальный ответ от ClaudeCodeService
            assert len(mcp_response) > 0
            # Проверяем что есть текст с упоминанием app
            assert any("app" in str(item).lower() for item in mcp_response)
    
    @pytest.mark.asyncio
    @patch('agent.tools.mcp_tool.claude_code_service')
    async def test_mcp_real_service_call(self, mock_service, mcp_tool):
        """Тест вызова реального ClaudeCodeService"""
        # Настраиваем мок
        mock_service.execute_mcp_command = AsyncMock(return_value={
            "success": True,
            "response": "Список приложений",
            "mcp_response": {"apps": [{"name": "test-app"}]},
            "execution_time": 1.5
        })
        
        # Включаем доступность сервиса
        with patch('agent.tools.mcp_tool.CLAUDE_SERVICE_AVAILABLE', True):
            params = MCPCommandParams(
                command="list apps",
                user_id="test_user"
            )
            
            response = await mcp_tool.execute(params)
            
            # Проверяем результат
            assert response.success is True
            assert response.data["response"] == "Список приложений"
            assert "apps" in response.data.get("mcp_response", {})
            
            # Проверяем, что сервис был вызван
            mock_service.execute_mcp_command.assert_called_once_with(
                "/mcp apps",
                "test_user"
            )
    
    def test_mcp_confirmation_message(self, mcp_tool):
        """Тест генерации сообщения подтверждения"""
        params = MCPCommandParams(
            command="show databases",
            user_id="test_user"
        )
        
        message = mcp_tool.get_confirmation_message(params)
        
        assert "Подтверждение MCP команды" in message
        assert "show databases" in message
        assert "databases" in message
        assert "✅ Да / ❌ Нет" in message


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
    async def test_tool_metadata(self):
        """Тест метаданных инструментов"""
        mcp_tool = MCPTool()
        youtube_tool = YouTubeAnalyzerTool()
        
        # Проверяем метаданные MCP
        mcp_meta = mcp_tool.get_metadata()
        assert mcp_meta.name == "mcp_executor"
        assert mcp_meta.requires_confirmation is True
        
        # Проверяем метаданные YouTube
        youtube_meta = youtube_tool.get_metadata()
        assert youtube_meta.name == "youtube_analyzer"
        assert youtube_meta.requires_confirmation is False
    
    @pytest.mark.asyncio
    async def test_openai_schemas(self):
        """Тест схем для OpenAI"""
        mcp_tool = MCPTool()
        youtube_tool = YouTubeAnalyzerTool()
        
        # Проверяем схему MCP
        mcp_schema = mcp_tool.get_openai_schema()
        assert mcp_schema["type"] == "function"
        assert "execute_mcp_command" in mcp_schema["function"]["name"]
        assert "command" in mcp_schema["function"]["parameters"]["properties"]
        
        # Проверяем схему YouTube
        youtube_schema = youtube_tool.get_openai_schema()
        assert youtube_schema["type"] == "function"
        assert "analyze_youtube_video" in youtube_schema["function"]["name"]
        assert "url" in youtube_schema["function"]["parameters"]["properties"]
        assert "extract_subtitles" in youtube_schema["function"]["parameters"]["properties"]


if __name__ == "__main__":
    # Запускаем тесты
    pytest.main([__file__, "-v", "--tb=short"])