"""
Тесты для Этапа 7: Интеграция Intelligent Agent с Telegram
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from pathlib import Path

# Добавляем путь к корню проекта
import sys
sys.path.append(str(Path(__file__).parent.parent))

from bot.webhook.handlers import WebhookHandler
from bot.services.intelligent_agent_service import IntelligentAgentService
from bot.core.interfaces import Message, User, UserRole, MessageType, Response
from agent.core.models import AgentResponse, ToolResponse, ToolType
from agent.core.intents import Intent


class TestIntelligentAgentService:
    """Тесты для IntelligentAgentService"""
    
    @pytest.fixture
    def mock_agent(self):
        """Создает мок IntelligentAgent"""
        agent = Mock()
        agent.process_message = AsyncMock()
        return agent
    
    @pytest.fixture
    def mock_tool_registry(self):
        """Создает мок ToolRegistry"""
        registry = Mock()
        registry.list_tools = Mock(return_value=["mcp_executor", "youtube_analyzer"])
        registry.get_tool = Mock()
        return registry
    
    @pytest.fixture
    def mock_confirmation_manager(self):
        """Создает мок ConfirmationManager"""
        manager = Mock()
        manager.get_user_state = Mock(return_value=None)
        manager.get_active_confirmations_count = Mock(return_value=0)
        manager.create_confirmation = Mock(return_value="session_123")
        manager.clear_user_state = Mock()
        return manager
    
    @pytest.fixture
    def intelligent_agent_service(self, mock_agent, mock_tool_registry, mock_confirmation_manager):
        """Создает IntelligentAgentService с моками"""
        service = IntelligentAgentService()
        # Заменяем компоненты моками
        service.agent = mock_agent
        service.tool_registry = mock_tool_registry
        service.confirmation_manager = mock_confirmation_manager
        service.enabled = True
        return service
    
    @pytest.fixture
    def admin_message(self):
        """Создает тестовое сообщение от админа"""
        user = User(
            id=123456,
            username="admin_user",
            first_name="Admin",
            last_name="User",
            role=UserRole.ADMIN
        )
        
        return Message(
            id=1,
            user=user,
            chat_id=123456,
            text="покажи все приложения",
            type=MessageType.TEXT,
            timestamp=datetime.now()
        )
    
    @pytest.mark.asyncio
    async def test_process_message_success(self, intelligent_agent_service, admin_message, mock_agent):
        """Тест успешной обработки сообщения"""
        # Настраиваем мок ответа агента
        agent_response = AgentResponse(
            message="Вот список приложений:\n- app1\n- app2",
            intent=Intent.MCP_COMMAND,
            confidence=0.95,
            tool_used=ToolType.MCP,
            requires_confirmation=False
        )
        mock_agent.process_message.return_value = agent_response
        
        # Обрабатываем сообщение
        response = await intelligent_agent_service.process_message(admin_message)
        
        # Проверяем результат
        assert response.metadata["success"] is True
        assert "Вот список приложений" in response.text
        assert "_🔧 Использован: mcp_" in response.text
        assert response.metadata["intent"] == "mcp_command"
        assert response.metadata["tool_used"] == "mcp_executor"
        assert response.metadata["confidence"] == 0.95
    
    @pytest.mark.asyncio
    async def test_process_message_with_confirmation(self, intelligent_agent_service, admin_message, mock_agent):
        """Тест обработки с запросом подтверждения"""
        # Настраиваем мок ответа с подтверждением
        tool_response = ToolResponse(
            success=True,
            data={"command": "delete app", "app_name": "test-app"}
        )
        
        agent_response = AgentResponse(
            message="Вы уверены что хотите удалить приложение test-app?",
            intent=Intent.MCP_COMMAND,
            confidence=0.9,
            tool_used=ToolType.MCP,
            requires_confirmation=True,
            tool_response=tool_response
        )
        mock_agent.process_message.return_value = agent_response
        
        # Обрабатываем сообщение
        response = await intelligent_agent_service.process_message(admin_message)
        
        # Проверяем результат
        assert response.metadata["success"] is True
        assert "Вы уверены" in response.text
        assert "✅ Да / ❌ Нет" in response.text
        assert response.metadata["confirmation_required"] is True
        assert response.metadata["session_id"] == "session_123"
    
    @pytest.mark.asyncio
    async def test_handle_confirmation_positive(self, intelligent_agent_service, mock_confirmation_manager, mock_tool_registry):
        """Тест обработки положительного подтверждения"""
        # Настраиваем состояние подтверждения
        confirmation_state = Mock()
        confirmation_state.tool_name = "mcp_executor"
        confirmation_state.parameters = Mock(command="delete app")
        mock_confirmation_manager.get_user_state.return_value = confirmation_state
        
        # Настраиваем мок инструмента
        mock_tool = Mock()
        mock_tool.execute = AsyncMock(return_value=ToolResponse(
            success=True,
            data={"message": "Приложение успешно удалено"}
        ))
        mock_tool_registry.get_tool.return_value = mock_tool
        
        # Создаем сообщение с подтверждением
        confirm_message = Mock()
        confirm_message.text = "да"
        confirm_message.user = Mock(id=123)
        
        # Обрабатываем подтверждение
        response = await intelligent_agent_service.process_message(confirm_message)
        
        # Проверяем результат
        assert response.metadata["success"] is True
        assert "✅ Приложение успешно удалено" in response.text
        mock_confirmation_manager.clear_user_state.assert_called_once_with("123")
    
    @pytest.mark.asyncio
    async def test_handle_confirmation_negative(self, intelligent_agent_service, mock_confirmation_manager):
        """Тест обработки отрицательного подтверждения"""
        # Настраиваем состояние подтверждения
        confirmation_state = Mock()
        mock_confirmation_manager.get_user_state.return_value = confirmation_state
        
        # Создаем сообщение с отказом
        cancel_message = Mock()
        cancel_message.text = "нет"
        cancel_message.user = Mock(id=123)
        
        # Обрабатываем отказ
        response = await intelligent_agent_service.process_message(cancel_message)
        
        # Проверяем результат
        assert response.metadata["success"] is True
        assert "❌ Операция отменена" in response.text
        mock_confirmation_manager.clear_user_state.assert_called_once_with("123")
    
    @pytest.mark.asyncio
    async def test_service_not_available(self):
        """Тест когда сервис недоступен"""
        service = IntelligentAgentService()
        service.enabled = False
        
        message = Mock()
        response = await service.process_message(message)
        
        assert response.metadata is None or response.metadata.get("success", False) is False
        assert "Intelligent Agent не доступен" in response.text
    
    def test_get_status(self, intelligent_agent_service):
        """Тест получения статуса сервиса"""
        status = intelligent_agent_service.get_status()
        
        assert status["enabled"] is True
        assert status["available"] is True
        assert status["tools"] == ["mcp_executor", "youtube_analyzer"]
        assert status["active_confirmations"] == 0


class TestWebhookIntegration:
    """Тесты интеграции с webhook handlers"""
    
    @pytest.fixture
    def webhook_handler(self):
        """Создает WebhookHandler"""
        return WebhookHandler()
    
    @pytest.fixture
    def admin_update(self):
        """Создает update от админа"""
        return {
            "update_id": 123,
            "message": {
                "message_id": 1,
                "from": {
                    "id": 123456,
                    "username": "admin_user",
                    "first_name": "Admin"
                },
                "chat": {"id": 123456},
                "text": "покажи приложения",
                "date": int(datetime.now().timestamp())
            }
        }
    
    @pytest.fixture
    def regular_user_update(self):
        """Создает update от обычного пользователя"""
        return {
            "update_id": 124,
            "message": {
                "message_id": 2,
                "from": {
                    "id": 789012,
                    "username": "regular_user",
                    "first_name": "User"
                },
                "chat": {"id": 789012},
                "text": "привет",
                "date": int(datetime.now().timestamp())
            }
        }
    
    @pytest.mark.asyncio
    @patch('bot.webhook.handlers.intelligent_agent_service')
    @patch('bot.webhook.handlers.is_admin')
    @patch('bot.telegram_bot.bot')
    async def test_admin_uses_intelligent_agent(self, mock_bot, mock_is_admin, mock_intelligent_service, webhook_handler, admin_update):
        """Тест что админы используют Intelligent Agent"""
        # Настраиваем моки
        mock_is_admin.return_value = True
        mock_intelligent_service.is_available.return_value = True
        mock_intelligent_service.process_message = AsyncMock(return_value=Response(
            text="Результат от Intelligent Agent",
            metadata={"success": True}
        ))
        mock_bot.send_message = Mock()
        
        # Обрабатываем update
        result = await webhook_handler.handle_update(admin_update)
        
        # Проверяем что использовался Intelligent Agent
        mock_intelligent_service.process_message.assert_called_once()
        mock_bot.send_message.assert_called_with(123456, "Результат от Intelligent Agent")
        assert result["ok"] is True
    
    @pytest.mark.asyncio
    @patch('bot.webhook.handlers.intelligent_agent_service')
    @patch('bot.webhook.handlers.is_admin')
    @patch('bot.core.agent.AgentFactory.get_agent')
    @patch('bot.telegram_bot.bot')
    async def test_regular_user_uses_standard_agent(self, mock_bot, mock_agent_factory, mock_is_admin, mock_intelligent_service, webhook_handler, regular_user_update):
        """Тест что обычные пользователи используют стандартный агент"""
        # Настраиваем моки
        mock_is_admin.return_value = False
        mock_intelligent_service.is_available.return_value = True
        
        # Создаем мок стандартного агента
        standard_agent = Mock()
        standard_agent.process_message = AsyncMock(return_value=Response(
            text="Результат от стандартного агента",
            metadata={"success": True}
        ))
        mock_agent_factory.return_value = standard_agent
        webhook_handler.agent = standard_agent
        
        mock_bot.send_message = Mock()
        
        # Обрабатываем update
        result = await webhook_handler.handle_update(regular_user_update)
        
        # Проверяем что НЕ использовался Intelligent Agent
        mock_intelligent_service.process_message.assert_not_called()
        standard_agent.process_message.assert_called_once()
        mock_bot.send_message.assert_called_with(789012, "Результат от стандартного агента")
        assert result["ok"] is True
    
    @pytest.mark.asyncio
    @patch('bot.webhook.handlers.intelligent_agent_service')
    @patch('bot.webhook.handlers.is_admin')
    @patch('bot.telegram_bot.bot')
    async def test_agent_command(self, mock_bot, mock_is_admin, mock_intelligent_service, webhook_handler):
        """Тест команды /agent"""
        # Настраиваем моки
        mock_is_admin.return_value = True
        mock_intelligent_service.get_status.return_value = {
            "enabled": True,
            "available": True,
            "tools": ["mcp_executor", "youtube_analyzer"],
            "active_confirmations": 2
        }
        mock_bot.send_message = Mock()
        
        # Создаем update с командой /agent
        agent_command_update = {
            "update_id": 125,
            "message": {
                "message_id": 3,
                "from": {
                    "id": 123456,
                    "username": "admin_user",
                    "first_name": "Admin"
                },
                "chat": {"id": 123456},
                "text": "/agent",
                "date": int(datetime.now().timestamp())
            }
        }
        
        # Обрабатываем команду
        result = await webhook_handler.handle_update(agent_command_update)
        
        # Проверяем ответ
        call_args = mock_bot.send_message.call_args
        assert call_args[0][0] == 123456  # chat_id
        status_text = call_args[0][1]
        assert "🧠 **Intelligent Agent Status**" in status_text
        assert "Enabled: ✅" in status_text
        assert "Available: ✅" in status_text
        assert "mcp_executor" in status_text
        assert "youtube_analyzer" in status_text
        assert "**Active Confirmations:** 2" in status_text
    
    @pytest.mark.asyncio
    @patch('bot.webhook.handlers.intelligent_agent_service', None)
    @patch('bot.webhook.handlers.is_admin')
    @patch('bot.telegram_bot.bot')
    async def test_agent_command_not_available(self, mock_bot, mock_is_admin, webhook_handler):
        """Тест команды /agent когда сервис недоступен"""
        # Настраиваем моки
        mock_is_admin.return_value = True
        mock_bot.send_message = Mock()
        
        # Создаем update с командой /agent
        agent_command_update = {
            "update_id": 126,
            "message": {
                "message_id": 4,
                "from": {
                    "id": 123456,
                    "username": "admin_user",
                    "first_name": "Admin"
                },
                "chat": {"id": 123456},
                "text": "/agent",
                "date": int(datetime.now().timestamp())
            }
        }
        
        # Обрабатываем команду
        result = await webhook_handler.handle_update(agent_command_update)
        
        # Проверяем ответ
        call_args = mock_bot.send_message.call_args
        assert call_args[0][0] == 123456  # chat_id
        assert "❌ Intelligent Agent Service не доступен" in call_args[0][1]


class TestHelperIntegration:
    """Тесты интеграции с help сообщениями"""
    
    @pytest.mark.asyncio
    @patch('bot.webhook.handlers.intelligent_agent_service')
    @patch('bot.webhook.handlers.claude_code_service', Mock())
    @patch('bot.webhook.handlers.is_admin')
    @patch('bot.telegram_bot.bot')
    async def test_help_shows_agent_info_for_admin(self, mock_bot, mock_is_admin, mock_intelligent_service):
        """Тест что help показывает информацию об агенте для админов"""
        # Настраиваем моки
        mock_is_admin.return_value = True
        mock_intelligent_service.is_available.return_value = True
        mock_bot.send_message = Mock()
        
        webhook_handler = WebhookHandler()
        
        # Создаем update с командой /help
        help_update = {
            "update_id": 127,
            "message": {
                "message_id": 5,
                "from": {
                    "id": 123456,
                    "username": "admin_user",
                    "first_name": "Admin"
                },
                "chat": {"id": 123456},
                "text": "/help",
                "date": int(datetime.now().timestamp())
            }
        }
        
        # Обрабатываем команду
        await webhook_handler.handle_update(help_update)
        
        # Проверяем что в help есть информация об агенте
        call_args = mock_bot.send_message.call_args
        help_text = call_args[0][1]
        assert "🧠 Intelligent Agent:" in help_text
        assert "/agent - Статус Intelligent Agent" in help_text
        assert "Автоматическая классификация намерений" in help_text
        assert "Обучение на ваших предпочтениях" in help_text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])