"""
Тесты для MCP Manager

Проверяет:
- Инициализацию и управление подключениями
- Выполнение функций
- Кэширование
- Обработку ошибок
- Метрики и статистику
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from datetime import datetime
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot.mcp_manager import MCPManager, MCPServerConnection, MCPFunctionResult


class TestMCPServerConnection:
    """Тесты для MCPServerConnection"""
    
    @pytest.fixture
    def mock_config(self):
        """Фикстура с тестовой конфигурацией сервера"""
        return {
            "name": "test_server",
            "display_name": "Test Server",
            "enabled": True,
            "url": "http://test.server",
            "headers": {"Authorization": "Bearer test"},
            "functions": {
                "test_function": {
                    "name": "test_function",
                    "description": "Test function",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "param1": {"type": "string"}
                        },
                        "required": ["param1"]
                    }
                }
            },
            "timeout": 30,
            "max_retries": 3
        }
    
    @pytest.mark.asyncio
    async def test_connection_initialization(self, mock_config):
        """Тест инициализации подключения"""
        connection = MCPServerConnection(mock_config)
        
        assert connection.name == "test_server"
        assert connection.url == "http://test.server"
        assert connection.enabled is True
        assert connection.timeout == 30
        assert connection.max_retries == 3
        assert "test_function" in connection.functions
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_config):
        """Тест успешной проверки здоровья"""
        connection = MCPServerConnection(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            result = await connection.health_check()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_config):
        """Тест неудачной проверки здоровья"""
        connection = MCPServerConnection(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_session.return_value.__aenter__.return_value.get.side_effect = Exception("Connection error")
            
            result = await connection.health_check()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_execute_function_success(self, mock_config):
        """Тест успешного выполнения функции"""
        connection = MCPServerConnection(mock_config)
        
        expected_result = {"success": True, "data": "test data"}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=expected_result)
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
            
            result = await connection.execute_function("test_function", {"param1": "value1"})
            
            assert result["success"] is True
            assert result["data"] == "test data"
    
    @pytest.mark.asyncio
    async def test_execute_function_with_retry(self, mock_config):
        """Тест выполнения функции с повторными попытками"""
        connection = MCPServerConnection(mock_config)
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Первые 2 попытки неудачные, третья успешная
            mock_response_fail = AsyncMock()
            mock_response_fail.status = 500
            
            mock_response_success = AsyncMock()
            mock_response_success.status = 200
            mock_response_success.json = AsyncMock(return_value={"success": True})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]
            
            result = await connection.execute_function("test_function", {"param1": "value1"})
            
            assert result["success"] is True
            assert mock_session.return_value.__aenter__.return_value.post.call_count == 1
    
    def test_validate_parameters(self, mock_config):
        """Тест валидации параметров"""
        connection = MCPServerConnection(mock_config)
        
        # Валидные параметры
        assert connection.validate_parameters("test_function", {"param1": "value"}) is True
        
        # Невалидные параметры (отсутствует обязательный)
        assert connection.validate_parameters("test_function", {}) is False
        
        # Несуществующая функция
        assert connection.validate_parameters("unknown_function", {}) is False


class TestMCPManager:
    """Тесты для MCPManager"""
    
    @pytest.fixture
    def mock_mcp_config(self):
        """Фикстура с тестовой конфигурацией MCP"""
        return {
            "servers": {
                "test_server": {
                    "name": "test_server",
                    "display_name": "Test Server",
                    "enabled": True,
                    "url": "http://test.server",
                    "functions": {
                        "test_server_function1": {
                            "name": "function1",
                            "description": "Test function 1"
                        }
                    }
                },
                "disabled_server": {
                    "name": "disabled_server",
                    "enabled": False
                }
            },
            "permissions": {
                "default": {
                    "test_server": ["read", "write"]
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, mock_mcp_config):
        """Тест инициализации менеджера"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            assert len(manager.servers) == 1
            assert "test_server" in manager.servers
            assert "disabled_server" not in manager.servers
    
    @pytest.mark.asyncio
    async def test_execute_function_success(self, mock_mcp_config):
        """Тест успешного выполнения функции через менеджер"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            # Мокаем выполнение функции
            mock_connection = AsyncMock()
            mock_connection.execute_function.return_value = {
                "success": True,
                "data": {"result": "test"}
            }
            manager.servers["test_server"] = mock_connection
            
            result = await manager.execute_function(
                "test_server_function1",
                {"param": "value"},
                user_id="test_user"
            )
            
            assert result.success is True
            assert result.data["result"] == "test"
            assert result.server == "test_server"
            assert result.function == "test_server_function1"
    
    @pytest.mark.asyncio
    async def test_execute_function_with_cache(self, mock_mcp_config):
        """Тест кэширования результатов"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            # Мокаем выполнение функции
            mock_connection = AsyncMock()
            mock_connection.execute_function.return_value = {
                "success": True,
                "data": {"result": "cached"}
            }
            manager.servers["test_server"] = mock_connection
            
            # Первый вызов
            result1 = await manager.execute_function(
                "test_server_function1",
                {"param": "value"},
                user_id="test_user"
            )
            
            # Второй вызов (должен вернуть из кэша)
            result2 = await manager.execute_function(
                "test_server_function1",
                {"param": "value"},
                user_id="test_user"
            )
            
            # Проверяем, что функция вызвана только один раз
            mock_connection.execute_function.assert_called_once()
            
            # Результаты должны быть одинаковыми
            assert result1.data == result2.data
            assert manager._cache_stats()["hits"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_function_permission_denied(self, mock_mcp_config):
        """Тест отказа в доступе"""
        # Модифицируем конфиг, убрав разрешения
        mock_mcp_config["permissions"]["default"]["test_server"] = []
        
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            result = await manager.execute_function(
                "test_server_function1",
                {"param": "value"},
                user_id="test_user"
            )
            
            assert result.success is False
            assert "permission" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_mcp_config):
        """Тест ограничения частоты запросов"""
        # Устанавливаем низкий лимит для теста
        mock_mcp_config["rate_limits"] = {
            "default": {
                "requests_per_minute": 2
            }
        }
        
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            mock_connection = AsyncMock()
            mock_connection.execute_function.return_value = {"success": True}
            manager.servers["test_server"] = mock_connection
            
            # Делаем 3 запроса подряд
            results = []
            for i in range(3):
                result = await manager.execute_function(
                    "test_server_function1",
                    {"param": f"value{i}"},
                    user_id="test_user"
                )
                results.append(result)
            
            # Первые 2 должны пройти, третий - нет
            assert results[0].success is True
            assert results[1].success is True
            assert results[2].success is False
            assert "rate limit" in results[2].error.lower()
    
    def test_get_metrics(self, mock_mcp_config):
        """Тест получения метрик"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            
            # Добавляем тестовые метрики
            manager.metrics["total_calls"] = 10
            manager.metrics["total_successful"] = 8
            manager.metrics["total_failed"] = 2
            
            metrics = manager.get_metrics()
            
            assert metrics["total_calls"] == 10
            assert metrics["total_successful"] == 8
            assert metrics["total_failed"] == 2
            assert metrics["average_execution_time"] >= 0
    
    @pytest.mark.asyncio
    async def test_get_status(self, mock_mcp_config):
        """Тест получения статуса"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            status = manager.get_status()
            
            assert status["initialized"] is True
            assert "test_server" in status["servers"]
            assert status["servers"]["test_server"]["enabled"] is True
            assert status["servers"]["test_server"]["functions_count"] == 1
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_mcp_config):
        """Тест корректного завершения работы"""
        with patch('bot.mcp_manager.MCPManager._load_config', return_value=mock_mcp_config):
            manager = MCPManager()
            await manager.initialize()
            
            # Мокаем HTTP сессию
            mock_session = AsyncMock()
            manager.servers["test_server"]._session = mock_session
            
            await manager.shutdown()
            
            # Проверяем, что сессии закрыты
            mock_session.close.assert_called_once()


class TestMCPFunctionResult:
    """Тесты для MCPFunctionResult"""
    
    def test_success_result(self):
        """Тест успешного результата"""
        result = MCPFunctionResult(
            success=True,
            data={"key": "value"},
            server="test_server",
            function="test_function",
            execution_time=0.5
        )
        
        assert result.success is True
        assert result.data["key"] == "value"
        assert result.error is None
        assert result.execution_time == 0.5
    
    def test_error_result(self):
        """Тест результата с ошибкой"""
        result = MCPFunctionResult(
            success=False,
            error="Test error",
            server="test_server",
            function="test_function",
            execution_time=0.1
        )
        
        assert result.success is False
        assert result.error == "Test error"
        assert result.data is None
    
    def test_result_serialization(self):
        """Тест сериализации результата"""
        result = MCPFunctionResult(
            success=True,
            data={"test": "data"},
            server="test_server",
            function="test_function",
            execution_time=1.0,
            cached=True
        )
        
        serialized = result.to_dict()
        
        assert serialized["success"] is True
        assert serialized["data"]["test"] == "data"
        assert serialized["cached"] is True
        assert "timestamp" in serialized


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])