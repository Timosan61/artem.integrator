"""
Тесты для Этапа 6: Memory и Learning
"""
import pytest
import asyncio
import os
import tempfile
import json
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к корню проекта
import sys
sys.path.append(str(Path(__file__).parent.parent))

from agent.core.preference_manager import PreferenceManager, PreferencePattern
from agent.core.models import ToolType
from agent.core.intents import Intent
from agent.core.intelligent_agent import IntelligentAgent
from bot.services.memory_manager import ZepMemoryManager, InMemoryManager


class TestPreferenceManager:
    """Тесты для менеджера предпочтений"""
    
    @pytest.fixture
    def temp_storage(self):
        """Создает временный файл для хранения предпочтений"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        # Удаляем после теста
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def preference_manager(self, temp_storage):
        """Создает экземпляр PreferenceManager с временным хранилищем"""
        return PreferenceManager(storage_path=temp_storage)
    
    def test_record_choice(self, preference_manager):
        """Тест записи выбора пользователя"""
        # Записываем выбор
        preference_manager.record_choice(
            user_id="test_user",
            message="покажи приложения",
            intent=Intent.MCP_COMMAND,
            tool_type=ToolType.MCP,
            success=True,
            tool_params={"command": "list apps"}
        )
        
        # Проверяем что выбор записан
        assert "test_user" in preference_manager.preferences
        pattern_key = f"{Intent.MCP_COMMAND.value}:{ToolType.MCP.value}"
        assert pattern_key in preference_manager.preferences["test_user"]
        
        pattern = preference_manager.preferences["test_user"][pattern_key]
        assert pattern.usage_count == 1
        assert pattern.success_count == 1
        assert pattern.success_rate == 1.0
    
    def test_multiple_recordings(self, preference_manager):
        """Тест множественных записей"""
        # Записываем несколько успешных и неуспешных выборов
        for i in range(5):
            preference_manager.record_choice(
                user_id="test_user",
                message=f"команда {i}",
                intent=Intent.MCP_COMMAND,
                tool_type=ToolType.MCP,
                success=i % 2 == 0  # Чередуем успех/неудача
            )
        
        pattern_key = f"{Intent.MCP_COMMAND.value}:{ToolType.MCP.value}"
        pattern = preference_manager.preferences["test_user"][pattern_key]
        
        assert pattern.usage_count == 5
        assert pattern.success_count == 3  # 0, 2, 4
        assert pattern.success_rate == 0.6
    
    def test_get_preferred_tool(self, preference_manager):
        """Тест получения предпочитаемого инструмента"""
        # Сначала нет предпочтений
        result = preference_manager.get_preferred_tool(
            "test_user",
            Intent.MCP_COMMAND,
            [ToolType.MCP, ToolType.ECHO]
        )
        assert result is None
        
        # Записываем достаточно использований для обучения
        for _ in range(4):
            preference_manager.record_choice(
                user_id="test_user",
                message="покажи приложения",
                intent=Intent.MCP_COMMAND,
                tool_type=ToolType.MCP,
                success=True
            )
        
        # Теперь должно быть предпочтение
        result = preference_manager.get_preferred_tool(
            "test_user",
            Intent.MCP_COMMAND,
            [ToolType.MCP, ToolType.ECHO]
        )
        
        assert result is not None
        tool_type, confidence = result
        assert tool_type == ToolType.MCP
        assert confidence > 0.8
    
    def test_preference_persistence(self, temp_storage):
        """Тест сохранения и загрузки предпочтений"""
        # Создаем первый менеджер и записываем предпочтения
        manager1 = PreferenceManager(storage_path=temp_storage)
        
        for _ in range(3):
            manager1.record_choice(
                user_id="test_user",
                message="анализируй видео",
                intent=Intent.YOUTUBE_ANALYSIS,
                tool_type=ToolType.YOUTUBE_ANALYZER,
                success=True
            )
        
        # Создаем второй менеджер с тем же файлом
        manager2 = PreferenceManager(storage_path=temp_storage)
        
        # Проверяем что предпочтения загружены
        pattern_key = f"{Intent.YOUTUBE_ANALYSIS.value}:{ToolType.YOUTUBE_ANALYZER.value}"
        assert "test_user" in manager2.preferences
        assert pattern_key in manager2.preferences["test_user"]
        assert manager2.preferences["test_user"][pattern_key].usage_count == 3
    
    def test_cleanup_old_preferences(self, preference_manager):
        """Тест очистки устаревших предпочтений"""
        # Создаем паттерн вручную с старой датой
        old_pattern = PreferencePattern(
            user_id="test_user",
            intent=Intent.MCP_COMMAND,
            tool_type=ToolType.MCP
        )
        old_pattern.usage_count = 5
        old_pattern.success_count = 5
        old_pattern.last_used = datetime.now() - timedelta(days=40)  # Старше TTL
        
        pattern_key = f"{Intent.MCP_COMMAND.value}:{ToolType.MCP.value}"
        preference_manager.preferences["test_user"] = {pattern_key: old_pattern}
        
        # Очищаем
        preference_manager.cleanup_old_preferences()
        
        # Проверяем что паттерн удален
        assert "test_user" not in preference_manager.preferences
    
    def test_user_statistics(self, preference_manager):
        """Тест получения статистики пользователя"""
        # Записываем разные типы использований
        tools_usage = [
            (ToolType.MCP, 10, 8),  # 10 использований, 8 успешных
            (ToolType.YOUTUBE_ANALYZER, 5, 5),  # 5 использований, все успешные
            (ToolType.ECHO, 2, 1)  # 2 использования, 1 успешное
        ]
        
        for tool_type, total, success in tools_usage:
            for i in range(total):
                preference_manager.record_choice(
                    user_id="test_user",
                    message=f"test {i}",
                    intent=Intent.GENERAL_QUESTION,
                    tool_type=tool_type,
                    success=i < success
                )
        
        # Получаем статистику
        stats = preference_manager.get_user_statistics("test_user")
        
        assert stats["total_patterns"] == 3
        assert stats["success_rate"] == (8 + 5 + 1) / (10 + 5 + 2)  # 14/17
        assert len(stats["favorite_tools"]) == 3
        assert stats["favorite_tools"][0][0] == ToolType.MCP.value  # Самый используемый


class TestMemoryIntegration:
    """Тесты интеграции с менеджерами памяти"""
    
    @pytest.mark.asyncio
    async def test_in_memory_manager(self):
        """Тест in-memory менеджера памяти"""
        manager = InMemoryManager(max_messages_per_user=10)
        
        # Создаем мок сообщение
        message = Mock()
        message.text = "Привет, как дела?"
        message.id = 123
        message.timestamp = datetime.now()
        message.type = Mock(value="text")
        message.user = Mock(full_name="Test User")
        
        # Создаем мок ответ
        response = Mock()
        response.text = "Отлично, спасибо!"
        
        # Добавляем сообщение
        await manager.add_message(user_id=1, message=message, response=response)
        
        # Получаем контекст
        context = await manager.get_context(user_id=1, limit=5)
        
        assert len(context) == 2  # Сообщение + ответ
        assert context[0]["role"] == "user"
        assert context[0]["content"] == "Привет, как дела?"
        assert context[1]["role"] == "assistant"
        assert context[1]["content"] == "Отлично, спасибо!"
    
    @pytest.mark.asyncio
    async def test_memory_search(self):
        """Тест поиска в памяти"""
        manager = InMemoryManager()
        
        # Добавляем несколько сообщений
        messages = [
            ("Расскажи про MCP", "MCP - это система управления"),
            ("Что такое Docker?", "Docker - это контейнеризация"),
            ("Как работает MCP?", "MCP использует API для управления")
        ]
        
        for user_msg, assistant_msg in messages:
            message = Mock()
            message.text = user_msg
            message.id = 1
            message.timestamp = datetime.now()
            message.type = Mock(value="text")
            message.user = Mock(full_name="Test User")
            
            response = Mock()
            response.text = assistant_msg
            
            await manager.add_message(user_id=1, message=message, response=response)
        
        # Ищем по ключевому слову
        results = await manager.search_memory(user_id=1, query="MCP")
        
        assert len(results) >= 2  # Должны найти минимум 2 сообщения с MCP
        assert any("MCP" in r["content"] for r in results)


class TestAgentWithPreferences:
    """Тесты агента с поддержкой предпочтений"""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Создает мок ответа OpenAI"""
        mock_message = Mock()
        mock_message.content = "Выполняю команду"
        mock_message.tool_calls = None
        
        mock_choice = Mock()
        mock_choice.message = mock_message
        
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        
        return mock_response
    
    @pytest.mark.asyncio
    @patch('agent.core.intelligent_agent.AsyncOpenAI')
    async def test_agent_records_preferences(self, mock_openai_class, mock_openai_response):
        """Тест что агент записывает предпочтения"""
        # Настраиваем мок OpenAI
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
        mock_openai_class.return_value = mock_client
        
        # Создаем агента с временным хранилищем предпочтений
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            agent = IntelligentAgent(api_key="test_key", model="gpt-4o")
            agent.preference_manager = PreferenceManager(storage_path=temp_path)
            
            # Обрабатываем сообщение
            response = await agent.process_message(
                message="покажи все приложения",
                user_id="test_user"
            )
            
            # Проверяем что намерение классифицировано
            assert response.intent is not None
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio  
    async def test_preference_learning_flow(self):
        """Тест полного цикла обучения предпочтениям"""
        # Создаем preference_manager
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            preference_manager = PreferenceManager(storage_path=temp_path)
            
            # Симулируем несколько использований одного инструмента
            for i in range(5):
                preference_manager.record_choice(
                    user_id="test_user",
                    message=f"проанализируй видео {i}",
                    intent=Intent.YOUTUBE_ANALYSIS,
                    tool_type=ToolType.YOUTUBE_ANALYZER,
                    success=True,
                    tool_params={"url": f"https://youtube.com/watch?v={i}"}
                )
            
            # Проверяем что предпочтение сформировано
            preferred = preference_manager.get_preferred_tool(
                "test_user",
                Intent.YOUTUBE_ANALYSIS,
                [ToolType.YOUTUBE_ANALYZER, ToolType.ECHO]
            )
            
            assert preferred is not None
            tool_type, confidence = preferred
            assert tool_type == ToolType.YOUTUBE_ANALYZER
            assert confidence > 0.9  # Высокая уверенность после 5 успешных использований
            
            # Экспортируем данные для обучения
            learning_data = preference_manager.export_learning_data()
            
            assert len(learning_data) >= 5
            assert all(d["intent"] == Intent.YOUTUBE_ANALYSIS.value for d in learning_data)
            assert all(d["tool_type"] == ToolType.YOUTUBE_ANALYZER.value for d in learning_data)
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


if __name__ == "__main__":
    # Запускаем тесты
    pytest.main([__file__, "-v", "--tb=short"])