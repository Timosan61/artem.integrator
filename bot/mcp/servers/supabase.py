"""
Supabase MCP Server
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from ..core.interfaces import (
    MCPServer, MCPServerConfig, MCPFunction, 
    MCPResult, MCPServerStatus, MCPFunctionType
)
from ..core.exceptions import MCPServerError, MCPAuthError, MCPFunctionError

logger = logging.getLogger(__name__)


class SupabaseMCPServer(MCPServer):
    """
    MCP сервер для работы с Supabase
    
    Поддерживает:
    - Управление проектами
    - Выполнение SQL запросов
    - Управление миграциями
    - Работа с Edge Functions
    """
    
    def __init__(self, config: MCPServerConfig):
        """Инициализация Supabase сервера"""
        super().__init__(config)
        self.base_url = config.api_url or "https://api.supabase.com"
        self.api_key = config.api_key
        
        # Определяем доступные функции
        self._functions = self._define_functions()
        
    def _define_functions(self) -> List[MCPFunction]:
        """Определяет доступные функции Supabase"""
        return [
            MCPFunction(
                name="list_projects",
                description="Получить список Supabase проектов",
                parameters={
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                server="supabase",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            ),
            MCPFunction(
                name="get_project",
                description="Получить информацию о проекте",
                parameters={
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "ID проекта"
                        }
                    },
                    "required": ["id"]
                },
                server="supabase",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            ),
            MCPFunction(
                name="execute_sql",
                description="Выполнить SQL запрос в базе данных",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID проекта"
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL запрос"
                        }
                    },
                    "required": ["project_id", "query"]
                },
                server="supabase",
                function_type=MCPFunctionType.WRITE,
                permissions=["write"],
                cache_enabled=False
            ),
            MCPFunction(
                name="list_tables",
                description="Получить список таблиц в базе данных",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID проекта"
                        },
                        "schemas": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Список схем для поиска",
                            "default": ["public"]
                        }
                    },
                    "required": ["project_id"]
                },
                server="supabase",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            ),
            MCPFunction(
                name="apply_migration",
                description="Применить миграцию к базе данных",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID проекта"
                        },
                        "name": {
                            "type": "string",
                            "description": "Имя миграции в snake_case"
                        },
                        "query": {
                            "type": "string",
                            "description": "SQL запрос миграции"
                        }
                    },
                    "required": ["project_id", "name", "query"]
                },
                server="supabase",
                function_type=MCPFunctionType.ADMIN,
                permissions=["admin"],
                cache_enabled=False
            ),
            MCPFunction(
                name="list_edge_functions",
                description="Получить список Edge Functions",
                parameters={
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "ID проекта"
                        }
                    },
                    "required": ["project_id"]
                },
                server="supabase",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            ),
            MCPFunction(
                name="search_docs",
                description="Поиск в документации Supabase",
                parameters={
                    "type": "object",
                    "properties": {
                        "graphql_query": {
                            "type": "string",
                            "description": "GraphQL запрос для поиска"
                        }
                    },
                    "required": ["graphql_query"]
                },
                server="supabase",
                function_type=MCPFunctionType.SEARCH,
                permissions=["read"]
            )
        ]
    
    async def connect(self) -> bool:
        """Подключение к Supabase серверу"""
        if not self.api_key:
            logger.error("❌ Supabase API key не указан")
            self.status = MCPServerStatus.ERROR
            self.last_error = "API key not provided"
            return False
        
        try:
            # Проверяем подключение простым запросом
            # В реальности здесь бы был вызов к Supabase API
            self.status = MCPServerStatus.CONNECTED
            self.connected_at = datetime.now()
            logger.info("✅ Подключен к Supabase")
            return True
            
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            self.last_error = str(e)
            logger.error(f"❌ Ошибка подключения к Supabase: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Отключение от Supabase сервера"""
        self.status = MCPServerStatus.DISCONNECTED
        logger.info("🔌 Отключен от Supabase")
        return True
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """
        Выполнение функции Supabase
        
        Args:
            function_name: Имя функции
            parameters: Параметры функции
            
        Returns:
            MCPResult: Результат выполнения
        """
        try:
            # Здесь должна быть реальная реализация вызовов к Supabase API
            # Сейчас возвращаем заглушки для демонстрации
            
            if function_name == "list_projects":
                return MCPResult(
                    success=True,
                    data=[
                        {
                            "id": "project-1",
                            "name": "My App",
                            "organization_id": "org-1",
                            "region": "us-east-1",
                            "created_at": "2024-01-01T00:00:00Z"
                        }
                    ],
                    server="supabase",
                    function="list_projects"
                )
            
            elif function_name == "execute_sql":
                query = parameters.get("query", "")
                # Проверка на безопасность запроса
                if any(word in query.upper() for word in ["DROP", "TRUNCATE", "DELETE"]):
                    return MCPResult(
                        success=False,
                        error="Опасный SQL запрос заблокирован",
                        server="supabase",
                        function="execute_sql"
                    )
                
                return MCPResult(
                    success=True,
                    data={
                        "rows": [],
                        "rowCount": 0,
                        "fields": []
                    },
                    server="supabase",
                    function="execute_sql"
                )
            
            else:
                return MCPResult(
                    success=False,
                    error=f"Функция {function_name} не реализована",
                    server="supabase",
                    function=function_name
                )
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения Supabase функции {function_name}: {e}")
            return MCPResult(
                success=False,
                error=str(e),
                server="supabase",
                function=function_name
            )
    
    async def get_available_functions(self) -> List[MCPFunction]:
        """Получение списка доступных функций"""
        return self._functions
    
    async def health_check(self) -> bool:
        """Проверка здоровья сервера"""
        try:
            # Простая проверка - можем ли мы получить список проектов
            result = await self.execute_function("list_projects", {})
            return result.success
        except Exception:
            return False