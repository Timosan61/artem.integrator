"""
Тесты для MCP Agent

Проверяет:
- Инициализацию агента
- Генерацию функций для OpenAI
- Обработку MCP запросов
- Маршрутизацию функций
- Fallback механизмы
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from typing import Dict, Any, List
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot.mcp_agent import MCPAgent, MCPFunction
from bot.mcp_manager import MCPManager, MCPFunctionResult


class TestMCPFunction:
    """Тесты для MCPFunction dataclass"""
    
    def test_mcp_function_creation(self):
        """Тест создания MCPFunction"""
        func = MCPFunction(
            name="test_function",
            description="Test function description",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string"}
                }
            },
            server="test_server"
        )
        
        assert func.name == "test_function"
        assert func.description == "Test function description"
        assert func.server == "test_server"
        assert "properties" in func.parameters
    
    def test_to_openai_format(self):
        """Тест конвертации в формат OpenAI"""
        func = MCPFunction(
            name="test_function",
            description="Test function",
            parameters={"type": "object"},
            server="test_server"
        )
        
        openai_format = func.to_openai_format()
        
        assert openai_format["name"] == "test_function"
        assert openai_format["description"] == "Test function"
        assert openai_format["parameters"] == {"type": "object"}


class TestMCPAgent:
    """Тесты для MCPAgent"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        manager = Mock(spec=MCPManager)
        manager.get_status.return_value = {
            "initialized": True,
            "servers": {
                "supabase": {
                    "enabled": True,
                    "functions_count": 5
                },
                "digitalocean": {
                    "enabled": True,
                    "functions_count": 3
                }
            }
        }
        return manager
    
    @pytest.fixture
    def mock_instruction(self):
        """Фикстура с тестовыми инструкциями"""
        return {
            "system_instruction": "You are a helpful assistant",
            "context": "Test context"
        }
    
    def test_agent_initialization(self, mock_mcp_manager, mock_instruction):
        """Тест инициализации агента"""
        agent = MCPAgent(
            openai_key="test_openai_key",
            anthropic_key="test_anthropic_key",
            instruction_file=mock_instruction,
            mcp_manager=mock_mcp_manager
        )
        
        assert agent.mcp_manager == mock_mcp_manager
        assert agent.openai_client is not None
        assert agent.anthropic_client is not None
        assert agent.instruction == mock_instruction
    
    @pytest.mark.asyncio
    async def test_can_handle_mcp_admin(self, mock_mcp_manager, mock_instruction):
        """Тест проверки прав на MCP для админа"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        with patch('bot.auth.is_mcp_admin', return_value=True):
            # Команды MCP
            assert await agent.can_handle_mcp("/mcp status", 123, "admin") is True
            assert await agent.can_handle_mcp("/db SELECT * FROM users", 123, "admin") is True
            assert await agent.can_handle_mcp("/deploy app-123", 123, "admin") is True
            assert await agent.can_handle_mcp("покажи все проекты supabase", 123, "admin") is True
            
            # Обычные сообщения
            assert await agent.can_handle_mcp("привет", 123, "admin") is False
    
    @pytest.mark.asyncio
    async def test_can_handle_mcp_non_admin(self, mock_mcp_manager, mock_instruction):
        """Тест проверки прав на MCP для не-админа"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        with patch('bot.auth.is_mcp_admin', return_value=False):
            assert await agent.can_handle_mcp("/mcp status", 456, "user") is False
            assert await agent.can_handle_mcp("/db SELECT * FROM users", 456, "user") is False
    
    def test_generate_mcp_functions(self, mock_mcp_manager, mock_instruction):
        """Тест генерации функций для OpenAI"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Мокаем конфигурацию
        mock_config = {
            "servers": {
                "supabase": {
                    "functions": {
                        "supabase_list_projects": {
                            "name": "list_projects",
                            "description": "List all projects",
                            "parameters": {"type": "object"}
                        }
                    }
                }
            }
        }
        
        with patch.object(agent, '_load_mcp_config', return_value=mock_config):
            functions = agent._generate_mcp_functions()
            
            assert len(functions) == 1
            assert functions[0].name == "supabase_list_projects"
            assert functions[0].server == "supabase"
    
    @pytest.mark.asyncio
    async def test_process_mcp_request_with_openai(self, mock_mcp_manager, mock_instruction):
        """Тест обработки MCP запроса через OpenAI"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Мокаем OpenAI ответ
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Вот список проектов:"
        mock_response.choices[0].message.tool_calls = [
            Mock(
                function=Mock(
                    name="supabase_list_projects",
                    arguments='{"limit": 10}'
                )
            )
        ]
        
        # Мокаем результат выполнения функции
        mock_mcp_result = MCPFunctionResult(
            success=True,
            data={"projects": [{"name": "Project 1"}]},
            server="supabase",
            function="list_projects"
        )
        
        with patch.object(agent.openai_client.chat.completions, 'create', return_value=mock_response):
            with patch.object(agent.mcp_manager, 'execute_function', return_value=mock_mcp_result):
                with patch.object(agent, '_format_mcp_response', return_value="✅ Найден 1 проект"):
                    result = await agent.process_mcp_request(
                        "покажи проекты",
                        "session_123",
                        "Test User",
                        123
                    )
                    
                    assert "проект" in result
    
    @pytest.mark.asyncio
    async def test_process_mcp_request_fallback(self, mock_mcp_manager, mock_instruction):
        """Тест fallback на обычный AI при ошибке MCP"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Мокаем ошибку OpenAI
        with patch.object(agent.openai_client.chat.completions, 'create', side_effect=Exception("API Error")):
            # Мокаем fallback ответ
            with patch.object(agent, 'generate_response', return_value="Fallback ответ"):
                result = await agent.process_mcp_request(
                    "покажи проекты",
                    "session_123",
                    "Test User",
                    123
                )
                
                assert result == "Fallback ответ"
    
    @pytest.mark.asyncio
    async def test_route_mcp_function(self, mock_mcp_manager, mock_instruction):
        """Тест маршрутизации MCP функций"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Успешное выполнение
        mock_result = MCPFunctionResult(
            success=True,
            data={"test": "data"},
            server="supabase",
            function="list_projects"
        )
        
        with patch.object(agent.mcp_manager, 'execute_function', return_value=mock_result):
            result = await agent._route_mcp_function(
                "supabase_list_projects",
                {"limit": 10},
                user_id=123
            )
            
            assert result["success"] is True
            assert result["data"]["test"] == "data"
    
    def test_format_mcp_response(self, mock_mcp_manager, mock_instruction):
        """Тест форматирования MCP ответов"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Тест форматирования списка проектов
        result = MCPFunctionResult(
            success=True,
            data={"projects": [{"name": "Project 1", "id": "123"}]},
            server="supabase",
            function="list_projects"
        )
        
        with patch('bot.formatters.mcp_formatter.mcp_formatter.format_project_list') as mock_format:
            mock_format.return_value = "📂 Проекты Supabase"
            
            formatted = agent._format_mcp_response(result)
            
            assert formatted == "📂 Проекты Supabase"
            mock_format.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_status(self, mock_mcp_manager, mock_instruction):
        """Тест получения статуса MCP"""
        agent = MCPAgent(
            openai_key="test_key",
            anthropic_key="test_anthropic_key",
            mcp_manager=mock_mcp_manager
        )
        
        status = await agent.get_status()
        
        assert status["mcp_enabled"] is True
        assert status["anthropic_available"] is True
        assert status["openai_available"] is True
        assert "servers" in status
    
    @pytest.mark.asyncio
    async def test_handle_command_routing(self, mock_mcp_manager, mock_instruction):
        """Тест маршрутизации команд"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # SQL команда
        with patch.object(agent, '_handle_sql_command') as mock_sql:
            mock_sql.return_value = "SQL результат"
            result = await agent._handle_command("/db SELECT * FROM users", 123)
            assert result == "SQL результат"
        
        # Deploy команда
        with patch.object(agent, '_handle_deploy_command') as mock_deploy:
            mock_deploy.return_value = "Deploy результат"
            result = await agent._handle_command("/deploy app-123", 123)
            assert result == "Deploy результат"
        
        # Docs команда
        with patch.object(agent, '_handle_docs_command') as mock_docs:
            mock_docs.return_value = "Docs результат"
            result = await agent._handle_command("/docs react hooks", 123)
            assert result == "Docs результат"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_mcp_manager, mock_instruction):
        """Тест обработки ошибок"""
        agent = MCPAgent(
            openai_key="test_key",
            mcp_manager=mock_mcp_manager
        )
        
        # Ошибка выполнения функции
        error_result = MCPFunctionResult(
            success=False,
            error="Database connection failed",
            server="supabase",
            function="execute_sql"
        )
        
        with patch.object(agent.mcp_manager, 'execute_function', return_value=error_result):
            result = await agent._route_mcp_function(
                "supabase_execute_sql",
                {"query": "SELECT * FROM users"},
                user_id=123
            )
            
            assert result["success"] is False
            assert "error" in result
            assert result["error"] == "Database connection failed"


# Интеграционные тесты
class TestMCPIntegration:
    """Интеграционные тесты MCP системы"""
    
    @pytest.mark.asyncio
    async def test_full_mcp_flow(self):
        """Тест полного цикла обработки MCP запроса"""
        # Создаем мок конфигурацию
        mock_config = {
            "servers": {
                "supabase": {
                    "name": "supabase",
                    "enabled": True,
                    "url": "http://mock.supabase",
                    "functions": {
                        "supabase_list_projects": {
                            "name": "list_projects",
                            "description": "List projects",
                            "parameters": {"type": "object"}
                        }
                    }
                }
            },
            "permissions": {
                "default": {
                    "supabase": ["read"]
                }
            }
        }
        
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_config):
            # Создаем менеджер и агента
            manager = MCPManager()
            await manager.initialize()
            
            agent = MCPAgent(
                openai_key="test_key",
                mcp_manager=manager
            )
            
            # Мокаем HTTP запрос
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={
                    "success": True,
                    "projects": [{"name": "Test Project"}]
                })
                mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
                
                # Мокаем проверку прав
                with patch('bot.auth.is_mcp_admin', return_value=True):
                    # Проверяем, что агент может обработать запрос
                    can_handle = await agent.can_handle_mcp("/mcp projects", 123, "admin")
                    assert can_handle is True


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])