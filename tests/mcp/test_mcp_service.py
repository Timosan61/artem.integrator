"""
Тесты для MCP Service Layer

Проверяет:
- SupabaseService
- DigitalOceanService
- Context7Service
- MCPServiceFactory
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import sys
import os

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from bot.services.mcp_service import (
    MCPService, SupabaseService, DigitalOceanService, 
    Context7Service, MCPServiceFactory
)
from bot.mcp_manager import MCPManager, MCPFunctionResult


class TestMCPService:
    """Тесты для базового MCPService"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        return Mock(spec=MCPManager)
    
    def test_service_initialization(self, mock_mcp_manager):
        """Тест инициализации базового сервиса"""
        service = MCPService(mock_mcp_manager, "test_server")
        
        assert service.mcp_manager == mock_mcp_manager
        assert service.server_name == "test_server"
        assert service.logger is not None
    
    @pytest.mark.asyncio
    async def test_execute_function(self, mock_mcp_manager):
        """Тест выполнения функции через сервис"""
        service = MCPService(mock_mcp_manager, "test_server")
        
        expected_result = MCPFunctionResult(
            success=True,
            data={"test": "data"},
            server="test_server",
            function="test_function"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=expected_result)
        
        result = await service.execute_function(
            "test_function",
            {"param": "value"},
            user_id="user123"
        )
        
        assert result == expected_result
        mock_mcp_manager.execute_function.assert_called_once_with(
            "test_server_test_function",
            {"param": "value"},
            "user123"
        )
    
    def test_format_error(self, mock_mcp_manager):
        """Тест форматирования ошибки"""
        service = MCPService(mock_mcp_manager, "test_server")
        
        error_msg = service.format_error("Connection failed")
        assert error_msg == "❌ Ошибка test_server: Connection failed"


class TestSupabaseService:
    """Тесты для SupabaseService"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        return Mock(spec=MCPManager)
    
    @pytest.fixture
    def supabase_service(self, mock_mcp_manager):
        """Фикстура с SupabaseService"""
        return SupabaseService(mock_mcp_manager)
    
    @pytest.mark.asyncio
    async def test_list_projects_success(self, supabase_service, mock_mcp_manager):
        """Тест успешного получения списка проектов"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"projects": [
                {"id": "proj1", "name": "Project 1"},
                {"id": "proj2", "name": "Project 2"}
            ]},
            server="supabase",
            function="list_projects"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await supabase_service.list_projects(user_id="user123")
        
        assert result["success"] is True
        assert len(result["projects"]) == 2
        assert result["count"] == 2
        assert result["projects"][0]["name"] == "Project 1"
    
    @pytest.mark.asyncio
    async def test_list_projects_failure(self, supabase_service, mock_mcp_manager):
        """Тест неудачного получения списка проектов"""
        mock_result = MCPFunctionResult(
            success=False,
            error="Authentication failed",
            server="supabase",
            function="list_projects"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await supabase_service.list_projects()
        
        assert result["success"] is False
        assert "Authentication failed" in result["error"]
        assert "❌ Ошибка supabase:" in result["message"]
    
    @pytest.mark.asyncio
    async def test_execute_sql_success(self, supabase_service, mock_mcp_manager):
        """Тест успешного выполнения SQL"""
        mock_result = MCPFunctionResult(
            success=True,
            data={
                "rows": [{"id": 1, "name": "Test"}],
                "affected_rows": 0
            },
            server="supabase",
            function="execute_sql",
            execution_time=0.123
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await supabase_service.execute_sql(
            "proj123",
            "SELECT * FROM users LIMIT 1",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert len(result["rows"]) == 1
        assert result["execution_time"] == 0.123
    
    @pytest.mark.asyncio
    async def test_execute_sql_validation_failure(self, supabase_service):
        """Тест валидации опасных SQL запросов"""
        dangerous_queries = [
            "DROP TABLE users",
            "DELETE FROM posts",
            "TRUNCATE users",
            "drop database test"
        ]
        
        for query in dangerous_queries:
            result = await supabase_service.execute_sql("proj123", query)
            assert result["success"] is False
            assert "запрещенные операции" in result["message"]
    
    @pytest.mark.asyncio
    async def test_create_project(self, supabase_service, mock_mcp_manager):
        """Тест создания проекта"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"project": {"id": "new-proj", "name": "New Project"}},
            server="supabase",
            function="create_project"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await supabase_service.create_project(
            "New Project",
            "org123",
            region="us-east-1",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["project"]["name"] == "New Project"
        assert "✅ Проект 'New Project' успешно создан" in result["message"]
    
    @pytest.mark.asyncio
    async def test_list_tables(self, supabase_service, mock_mcp_manager):
        """Тест получения списка таблиц"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"tables": [
                {"name": "users", "schema": "public"},
                {"name": "posts", "schema": "public"}
            ]},
            server="supabase",
            function="list_tables"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await supabase_service.list_tables(
            "proj123",
            schemas=["public", "auth"],
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["count"] == 2
        assert result["schemas"] == ["public", "auth"]


class TestDigitalOceanService:
    """Тесты для DigitalOceanService"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        return Mock(spec=MCPManager)
    
    @pytest.fixture
    def do_service(self, mock_mcp_manager):
        """Фикстура с DigitalOceanService"""
        return DigitalOceanService(mock_mcp_manager)
    
    @pytest.mark.asyncio
    async def test_list_apps(self, do_service, mock_mcp_manager):
        """Тест получения списка приложений"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"apps": [
                {"id": "app1", "name": "Web App"},
                {"id": "app2", "name": "API"}
            ]},
            server="digitalocean",
            function="list_apps"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await do_service.list_apps(page=1, per_page=20)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert result["page"] == 1
        assert result["apps"][0]["name"] == "Web App"
    
    @pytest.mark.asyncio
    async def test_get_app_logs(self, do_service, mock_mcp_manager):
        """Тест получения логов приложения"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"logs": "Application started successfully\nListening on port 8080"},
            server="digitalocean",
            function="get_app_logs"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await do_service.get_app_logs(
            "app123",
            log_type="RUN",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert "Application started successfully" in result["logs"]
        assert result["log_type"] == "RUN"
        assert "timestamp" in result
    
    @pytest.mark.asyncio
    async def test_create_deployment(self, do_service, mock_mcp_manager):
        """Тест создания деплоя"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"deployment": {"id": "deploy123", "status": "pending"}},
            server="digitalocean",
            function="create_deployment"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await do_service.create_deployment(
            "app123",
            force_build=True,
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["deployment_id"] == "deploy123"
        assert "✅ Деплой запущен" in result["message"]
    
    @pytest.mark.asyncio
    async def test_get_deployment_status(self, do_service, mock_mcp_manager):
        """Тест получения статуса деплоя"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"deployment": {
                "id": "deploy123",
                "phase": "building",
                "progress": 45
            }},
            server="digitalocean",
            function="get_deployment"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await do_service.get_deployment_status(
            "app123",
            "deploy123",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["status"] == "building"
        assert result["status_emoji"] == "🔨"
        assert result["progress"] == 45


class TestContext7Service:
    """Тесты для Context7Service"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        return Mock(spec=MCPManager)
    
    @pytest.fixture
    def ctx7_service(self, mock_mcp_manager):
        """Фикстура с Context7Service"""
        return Context7Service(mock_mcp_manager)
    
    @pytest.mark.asyncio
    async def test_search_docs(self, ctx7_service, mock_mcp_manager):
        """Тест поиска документации"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"results": [
                {
                    "title": "React Hooks",
                    "url": "https://docs.react.com/hooks",
                    "snippet": "Learn about React hooks..."
                }
            ]},
            server="context7",
            function="search_docs"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await ctx7_service.search_docs(
            "react",
            "hooks",
            limit=5,
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["library"] == "react"
        assert result["query"] == "hooks"
        assert result["results"][0]["title"] == "React Hooks"
    
    @pytest.mark.asyncio
    async def test_get_library_docs(self, ctx7_service, mock_mcp_manager):
        """Тест получения документации библиотеки"""
        mock_result = MCPFunctionResult(
            success=True,
            data={
                "content": "# React Documentation\n\nReact is a JavaScript library...",
                "url": "https://docs.react.com"
            },
            server="context7",
            function="get_library_docs"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await ctx7_service.get_library_docs(
            "react",
            topic="components",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert "React Documentation" in result["documentation"]
        assert result["library"] == "react"
        assert result["topic"] == "components"
        assert result["url"] == "https://docs.react.com"
    
    @pytest.mark.asyncio
    async def test_get_code_examples(self, ctx7_service, mock_mcp_manager):
        """Тест получения примеров кода"""
        mock_result = MCPFunctionResult(
            success=True,
            data={"examples": [
                {
                    "title": "useState Example",
                    "code": "const [count, setCount] = useState(0);",
                    "language": "javascript",
                    "description": "Basic state hook usage"
                }
            ]},
            server="context7",
            function="get_code_examples"
        )
        
        mock_mcp_manager.execute_function = AsyncMock(return_value=mock_result)
        
        result = await ctx7_service.get_code_examples(
            "react",
            "hooks",
            language="javascript",
            user_id="user123"
        )
        
        assert result["success"] is True
        assert result["count"] == 1
        assert result["examples"][0]["title"] == "useState Example"
        assert "useState(0)" in result["examples"][0]["code"]


class TestMCPServiceFactory:
    """Тесты для MCPServiceFactory"""
    
    @pytest.fixture
    def mock_mcp_manager(self):
        """Фикстура с мок MCP Manager"""
        return Mock(spec=MCPManager)
    
    def test_factory_initialization(self, mock_mcp_manager):
        """Тест инициализации фабрики"""
        factory = MCPServiceFactory(mock_mcp_manager)
        
        assert factory.mcp_manager == mock_mcp_manager
        assert len(factory._services) == 0
    
    def test_get_supabase_service(self, mock_mcp_manager):
        """Тест получения Supabase сервиса"""
        factory = MCPServiceFactory(mock_mcp_manager)
        
        # Первый вызов создает сервис
        service1 = factory.get_supabase_service()
        assert isinstance(service1, SupabaseService)
        assert "supabase" in factory._services
        
        # Второй вызов возвращает тот же экземпляр
        service2 = factory.get_supabase_service()
        assert service1 is service2
    
    def test_get_digitalocean_service(self, mock_mcp_manager):
        """Тест получения DigitalOcean сервиса"""
        factory = MCPServiceFactory(mock_mcp_manager)
        
        service = factory.get_digitalocean_service()
        assert isinstance(service, DigitalOceanService)
        assert "digitalocean" in factory._services
    
    def test_get_context7_service(self, mock_mcp_manager):
        """Тест получения Context7 сервиса"""
        factory = MCPServiceFactory(mock_mcp_manager)
        
        service = factory.get_context7_service()
        assert isinstance(service, Context7Service)
        assert "context7" in factory._services
    
    def test_get_service_by_name(self, mock_mcp_manager):
        """Тест получения сервиса по имени"""
        factory = MCPServiceFactory(mock_mcp_manager)
        
        # Существующие сервисы
        supabase = factory.get_service("supabase")
        assert isinstance(supabase, SupabaseService)
        
        digitalocean = factory.get_service("digitalocean")
        assert isinstance(digitalocean, DigitalOceanService)
        
        context7 = factory.get_service("context7")
        assert isinstance(context7, Context7Service)
        
        # Несуществующий сервис
        unknown = factory.get_service("unknown")
        assert unknown is None


# Запуск тестов
if __name__ == "__main__":
    pytest.main([__file__, "-v"])