"""
MCP Service - Сервисный слой для работы с MCP серверами

Предоставляет высокоуровневые абстракции для работы с:
- Supabase (базы данных, проекты)
- DigitalOcean (приложения, деплои)
- Context7 (документация, примеры)
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from ..mcp_manager import MCPManager, MCPFunctionResult

logger = logging.getLogger(__name__)


class MCPService:
    """Базовый класс для MCP сервисов"""
    
    def __init__(self, mcp_manager: MCPManager, server_name: str):
        self.mcp_manager = mcp_manager
        self.server_name = server_name
        self.logger = logging.getLogger(f"{__name__}.{server_name}")
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> MCPFunctionResult:
        """Выполняет функцию через MCP Manager"""
        full_function_name = f"{self.server_name}_{function_name}"
        return await self.mcp_manager.execute_function(
            full_function_name, 
            parameters,
            user_id
        )
    
    def format_error(self, error: str) -> str:
        """Форматирует сообщение об ошибке"""
        return f"❌ Ошибка {self.server_name}: {error}"


class SupabaseService(MCPService):
    """Сервис для работы с Supabase"""
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__(mcp_manager, "supabase")
    
    async def list_projects(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Получает список всех проектов Supabase
        
        Returns:
            Dict с информацией о проектах или ошибкой
        """
        self.logger.info(f"Получение списка проектов для пользователя {user_id}")
        
        result = await self.execute_function("list_projects", {}, user_id)
        
        if result.success:
            projects = result.data.get("projects", [])
            self.logger.info(f"Найдено {len(projects)} проектов")
            return {
                "success": True,
                "projects": projects,
                "count": len(projects)
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить список проектов")
            }
    
    async def execute_sql(
        self, 
        project_id: str, 
        query: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет SQL запрос в базе данных
        
        Args:
            project_id: ID проекта Supabase
            query: SQL запрос
            user_id: ID пользователя
            
        Returns:
            Dict с результатами запроса или ошибкой
        """
        self.logger.info(f"Выполнение SQL в проекте {project_id}: {query[:50]}...")
        
        # Валидация запроса
        if not self._validate_sql_query(query):
            return {
                "success": False,
                "error": "Недопустимый SQL запрос",
                "message": "❌ Запрос содержит запрещенные операции"
            }
        
        result = await self.execute_function(
            "execute_sql",
            {"project_id": project_id, "query": query},
            user_id
        )
        
        if result.success:
            return {
                "success": True,
                "rows": result.data.get("rows", []),
                "affected_rows": result.data.get("affected_rows", 0),
                "execution_time": result.execution_time
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Ошибка выполнения SQL")
            }
    
    async def create_project(
        self,
        name: str,
        organization_id: str,
        region: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает новый проект Supabase
        
        Args:
            name: Название проекта
            organization_id: ID организации
            region: Регион размещения
            user_id: ID пользователя
            
        Returns:
            Dict с информацией о созданном проекте
        """
        self.logger.info(f"Создание проекта '{name}' в организации {organization_id}")
        
        parameters = {
            "name": name,
            "organization_id": organization_id
        }
        if region:
            parameters["region"] = region
        
        result = await self.execute_function("create_project", parameters, user_id)
        
        if result.success:
            return {
                "success": True,
                "project": result.data.get("project", {}),
                "message": f"✅ Проект '{name}' успешно создан"
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось создать проект")
            }
    
    async def list_tables(
        self,
        project_id: str,
        schemas: List[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает список таблиц в базе данных
        
        Args:
            project_id: ID проекта
            schemas: Список схем для поиска
            user_id: ID пользователя
            
        Returns:
            Dict со списком таблиц
        """
        self.logger.info(f"Получение списка таблиц для проекта {project_id}")
        
        parameters = {"project_id": project_id}
        if schemas:
            parameters["schemas"] = schemas
        
        result = await self.execute_function("list_tables", parameters, user_id)
        
        if result.success:
            tables = result.data.get("tables", [])
            return {
                "success": True,
                "tables": tables,
                "count": len(tables),
                "schemas": schemas or ["public"]
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить список таблиц")
            }
    
    def _validate_sql_query(self, query: str) -> bool:
        """Валидирует SQL запрос на безопасность"""
        # Простая проверка на опасные операции
        dangerous_keywords = [
            "drop table", "drop database", "delete from",
            "truncate", "drop schema", "drop user"
        ]
        
        query_lower = query.lower()
        for keyword in dangerous_keywords:
            if keyword in query_lower:
                return False
        
        return True


class DigitalOceanService(MCPService):
    """Сервис для работы с DigitalOcean"""
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__(mcp_manager, "digitalocean")
    
    async def list_apps(
        self,
        page: int = 1,
        per_page: int = 20,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает список приложений
        
        Args:
            page: Номер страницы
            per_page: Количество на странице
            user_id: ID пользователя
            
        Returns:
            Dict со списком приложений
        """
        self.logger.info(f"Получение списка приложений (страница {page})")
        
        result = await self.execute_function(
            "list_apps",
            {"page": page, "per_page": per_page},
            user_id
        )
        
        if result.success:
            apps = result.data.get("apps", [])
            return {
                "success": True,
                "apps": apps,
                "count": len(apps),
                "page": page,
                "per_page": per_page
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить список приложений")
            }
    
    async def get_app_logs(
        self,
        app_id: str,
        log_type: str = "RUN",
        deployment_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает логи приложения
        
        Args:
            app_id: ID приложения
            log_type: Тип логов (BUILD, DEPLOY, RUN)
            deployment_id: ID конкретного деплоя
            user_id: ID пользователя
            
        Returns:
            Dict с логами
        """
        self.logger.info(f"Получение логов {log_type} для приложения {app_id}")
        
        parameters = {
            "app_id": app_id,
            "type": log_type
        }
        if deployment_id:
            parameters["deployment_id"] = deployment_id
        
        result = await self.execute_function("get_app_logs", parameters, user_id)
        
        if result.success:
            return {
                "success": True,
                "logs": result.data.get("logs", ""),
                "app_id": app_id,
                "log_type": log_type,
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить логи")
            }
    
    async def create_deployment(
        self,
        app_id: str,
        force_build: bool = False,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создает новый деплой приложения
        
        Args:
            app_id: ID приложения
            force_build: Принудительная пересборка
            user_id: ID пользователя
            
        Returns:
            Dict с информацией о деплое
        """
        self.logger.info(f"Создание деплоя для приложения {app_id}")
        
        result = await self.execute_function(
            "create_deployment",
            {"app_id": app_id, "force_build": force_build},
            user_id
        )
        
        if result.success:
            deployment = result.data.get("deployment", {})
            return {
                "success": True,
                "deployment": deployment,
                "deployment_id": deployment.get("id"),
                "message": f"✅ Деплой запущен для приложения {app_id}"
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось создать деплой")
            }
    
    async def get_deployment_status(
        self,
        app_id: str,
        deployment_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает статус деплоя
        
        Args:
            app_id: ID приложения
            deployment_id: ID деплоя
            user_id: ID пользователя
            
        Returns:
            Dict со статусом деплоя
        """
        self.logger.info(f"Проверка статуса деплоя {deployment_id}")
        
        result = await self.execute_function(
            "get_deployment",
            {"app_id": app_id, "deployment_id": deployment_id},
            user_id
        )
        
        if result.success:
            deployment = result.data.get("deployment", {})
            status = deployment.get("phase", "unknown")
            
            # Определяем эмодзи для статуса
            status_emoji = {
                "pending": "⏳",
                "building": "🔨",
                "deploying": "🚀",
                "active": "✅",
                "error": "❌",
                "canceled": "🚫"
            }.get(status, "❓")
            
            return {
                "success": True,
                "deployment": deployment,
                "status": status,
                "status_emoji": status_emoji,
                "progress": deployment.get("progress", 0),
                "message": f"{status_emoji} Статус: {status}"
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить статус деплоя")
            }


class Context7Service(MCPService):
    """Сервис для работы с Context7 документацией"""
    
    def __init__(self, mcp_manager: MCPManager):
        super().__init__(mcp_manager, "context7")
    
    async def search_docs(
        self,
        library_name: str,
        query: str,
        limit: int = 5,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Поиск в документации библиотеки
        
        Args:
            library_name: Название библиотеки
            query: Поисковый запрос
            limit: Максимум результатов
            user_id: ID пользователя
            
        Returns:
            Dict с результатами поиска
        """
        self.logger.info(f"Поиск '{query}' в документации {library_name}")
        
        result = await self.execute_function(
            "search_docs",
            {
                "library_name": library_name,
                "query": query,
                "limit": limit
            },
            user_id
        )
        
        if result.success:
            results = result.data.get("results", [])
            return {
                "success": True,
                "results": results,
                "count": len(results),
                "library": library_name,
                "query": query
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось найти документацию")
            }
    
    async def get_library_docs(
        self,
        library_name: str,
        topic: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает документацию библиотеки
        
        Args:
            library_name: Название библиотеки
            topic: Конкретная тема
            user_id: ID пользователя
            
        Returns:
            Dict с документацией
        """
        self.logger.info(f"Получение документации {library_name}, тема: {topic}")
        
        parameters = {"library_name": library_name}
        if topic:
            parameters["topic"] = topic
        
        result = await self.execute_function("get_library_docs", parameters, user_id)
        
        if result.success:
            return {
                "success": True,
                "documentation": result.data.get("content", ""),
                "library": library_name,
                "topic": topic,
                "url": result.data.get("url", "")
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить документацию")
            }
    
    async def get_code_examples(
        self,
        library_name: str,
        topic: str,
        language: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получает примеры кода
        
        Args:
            library_name: Название библиотеки
            topic: Тема примеров
            language: Язык программирования
            user_id: ID пользователя
            
        Returns:
            Dict с примерами кода
        """
        self.logger.info(f"Получение примеров кода {library_name}/{topic}")
        
        parameters = {
            "library_name": library_name,
            "topic": topic
        }
        if language:
            parameters["language"] = language
        
        result = await self.execute_function("get_code_examples", parameters, user_id)
        
        if result.success:
            examples = result.data.get("examples", [])
            return {
                "success": True,
                "examples": examples,
                "count": len(examples),
                "library": library_name,
                "topic": topic
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "message": self.format_error(result.error or "Не удалось получить примеры кода")
            }


class MCPServiceFactory:
    """Фабрика для создания MCP сервисов"""
    
    def __init__(self, mcp_manager: MCPManager):
        self.mcp_manager = mcp_manager
        self._services = {}
    
    def get_supabase_service(self) -> SupabaseService:
        """Получает или создает Supabase сервис"""
        if "supabase" not in self._services:
            self._services["supabase"] = SupabaseService(self.mcp_manager)
        return self._services["supabase"]
    
    def get_digitalocean_service(self) -> DigitalOceanService:
        """Получает или создает DigitalOcean сервис"""
        if "digitalocean" not in self._services:
            self._services["digitalocean"] = DigitalOceanService(self.mcp_manager)
        return self._services["digitalocean"]
    
    def get_context7_service(self) -> Context7Service:
        """Получает или создает Context7 сервис"""
        if "context7" not in self._services:
            self._services["context7"] = Context7Service(self.mcp_manager)
        return self._services["context7"]
    
    def get_service(self, server_name: str) -> Optional[MCPService]:
        """Получает сервис по имени сервера"""
        if server_name == "supabase":
            return self.get_supabase_service()
        elif server_name == "digitalocean":
            return self.get_digitalocean_service()
        elif server_name == "context7":
            return self.get_context7_service()
        return None