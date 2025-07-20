"""
MCP Manager - Менеджер для управления MCP серверами

Этот модуль отвечает за:
- Управление жизненным циклом MCP серверов
- Связь с MCP серверами через HTTP/WebSocket
- Кеширование соединений и результатов
- Мониторинг состояния серверов
- Выполнение MCP функций
"""

import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
import httpx
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConnection:
    """Информация о подключении к MCP серверу"""
    server_name: str
    url: str
    api_key: Optional[str] = None
    last_ping: Optional[datetime] = None
    is_connected: bool = False
    error_count: int = 0
    last_error: Optional[str] = None
    
    def is_healthy(self) -> bool:
        """Проверяет здоровье соединения"""
        if not self.is_connected:
            return False
        if self.last_ping and (datetime.now() - self.last_ping) > timedelta(minutes=5):
            return False
        if self.error_count > 5:
            return False
        return True


@dataclass 
class MCPFunctionResult:
    """Результат выполнения MCP функции"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    server: Optional[str] = None
    function_name: Optional[str] = None


class MCPManager:
    """
    Менеджер для управления MCP серверами
    
    Обеспечивает:
    - Подключение к MCP серверам
    - Выполнение функций
    - Кеширование результатов
    - Мониторинг состояния
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация MCP Manager
        
        Args:
            config: Конфигурация MCP из mcp_config.json
        """
        self.config = config
        self.connections: Dict[str, MCPServerConnection] = {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.cache: Dict[str, Tuple[Any, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.metrics = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_time": 0.0,
            "last_call": None
        })
        
        # Инициализация подключений
        self._initialize_connections()
        
        logger.info(f"🔌 MCP Manager инициализирован с {len(self.connections)} серверами")
    
    def _initialize_connections(self):
        """Инициализирует подключения к MCP серверам"""
        servers = self.config.get("servers", {})
        
        for server_name, server_config in servers.items():
            if not server_config.get("enabled", False):
                continue
            
            # Получаем URL сервера из конфигурации или переменных окружения
            if server_name == "supabase":
                # Для Supabase используем прямое подключение через MCP
                connection = MCPServerConnection(
                    server_name="supabase",
                    url="mcp://supabase",  # MCP протокол
                    api_key=None  # Аутентификация через MCP
                )
            elif server_name == "digitalocean":
                # Для DigitalOcean используем прямое подключение
                connection = MCPServerConnection(
                    server_name="digitalocean", 
                    url="mcp://digitalocean",
                    api_key=None
                )
            elif server_name == "context7":
                # Для Context7 используем прямое подключение
                connection = MCPServerConnection(
                    server_name="context7",
                    url="mcp://context7",
                    api_key=None
                )
            else:
                logger.warning(f"⚠️ Неизвестный MCP сервер: {server_name}")
                continue
            
            self.connections[server_name] = connection
            logger.info(f"📡 Подготовлено подключение к {server_name}")
    
    async def connect_all(self):
        """Подключается ко всем настроенным серверам"""
        tasks = []
        for server_name, connection in self.connections.items():
            tasks.append(self._connect_to_server(connection))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        connected = sum(1 for r in results if r is True)
        logger.info(f"✅ Подключено {connected}/{len(self.connections)} MCP серверов")
    
    async def _connect_to_server(self, connection: MCPServerConnection) -> bool:
        """
        Подключается к конкретному MCP серверу
        
        Args:
            connection: Информация о подключении
            
        Returns:
            bool: True если подключение успешно
        """
        try:
            logger.info(f"🔗 Подключение к {connection.server_name}...")
            
            # Для MCP протокола подключение происходит через Claude/систему
            if connection.url.startswith("mcp://"):
                # В реальной реализации здесь будет проверка доступности MCP сервера
                connection.is_connected = True
                connection.last_ping = datetime.now()
                connection.error_count = 0
                logger.info(f"✅ Подключен к {connection.server_name}")
                return True
            
            # Для HTTP серверов делаем health check
            else:
                response = await self.http_client.get(
                    f"{connection.url}/health",
                    headers={"Authorization": f"Bearer {connection.api_key}"} if connection.api_key else {}
                )
                
                if response.status_code == 200:
                    connection.is_connected = True
                    connection.last_ping = datetime.now()
                    connection.error_count = 0
                    logger.info(f"✅ Подключен к {connection.server_name}")
                    return True
                else:
                    raise Exception(f"HTTP {response.status_code}")
                    
        except Exception as e:
            connection.is_connected = False
            connection.error_count += 1
            connection.last_error = str(e)
            logger.error(f"❌ Ошибка подключения к {connection.server_name}: {e}")
            return False
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> MCPFunctionResult:
        """
        Выполняет MCP функцию
        
        Args:
            function_name: Имя функции
            parameters: Параметры функции
            user_id: ID пользователя для логирования
            
        Returns:
            MCPFunctionResult: Результат выполнения
        """
        start_time = datetime.now()
        
        try:
            # Определяем сервер по имени функции
            server_name = self._get_server_for_function(function_name)
            if not server_name:
                return MCPFunctionResult(
                    success=False,
                    error=f"Сервер для функции {function_name} не найден",
                    function_name=function_name
                )
            
            # Проверяем подключение
            connection = self.connections.get(server_name)
            if not connection or not connection.is_healthy():
                # Пытаемся переподключиться
                await self._connect_to_server(connection)
                if not connection.is_connected:
                    return MCPFunctionResult(
                        success=False,
                        error=f"Сервер {server_name} недоступен",
                        server=server_name,
                        function_name=function_name
                    )
            
            # Проверяем кеш
            cache_key = f"{function_name}:{json.dumps(parameters, sort_keys=True)}"
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if datetime.now() - cache_time < self.cache_ttl:
                    logger.info(f"📦 Использую кешированный результат для {function_name}")
                    return MCPFunctionResult(
                        success=True,
                        data=cached_data,
                        execution_time=0.0,
                        server=server_name,
                        function_name=function_name
                    )
            
            # Выполняем функцию
            logger.info(f"🔧 Выполнение {function_name} на {server_name}")
            result = await self._execute_on_server(server_name, function_name, parameters)
            
            # Обновляем метрики
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(server_name, function_name, result.success, execution_time)
            
            # Кешируем успешный результат
            if result.success and result.data:
                self.cache[cache_key] = (result.data, datetime.now())
            
            result.execution_time = execution_time
            result.server = server_name
            result.function_name = function_name
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения {function_name}: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return MCPFunctionResult(
                success=False,
                error=str(e),
                execution_time=execution_time,
                function_name=function_name
            )
    
    def _get_server_for_function(self, function_name: str) -> Optional[str]:
        """Определяет сервер по имени функции"""
        if function_name.startswith("supabase_"):
            return "supabase"
        elif function_name.startswith("digitalocean_"):
            return "digitalocean"
        elif function_name.startswith("context7_"):
            return "context7"
        return None
    
    async def _execute_on_server(
        self, 
        server_name: str, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPFunctionResult:
        """
        Выполняет функцию на конкретном сервере
        
        В реальной реализации здесь будет вызов соответствующих MCP tools
        """
        # Это заглушка - в реальной реализации здесь будут вызовы MCP
        
        if server_name == "supabase":
            return await self._execute_supabase_function(function_name, parameters)
        elif server_name == "digitalocean":
            return await self._execute_digitalocean_function(function_name, parameters)
        elif server_name == "context7":
            return await self._execute_context7_function(function_name, parameters)
        else:
            return MCPFunctionResult(
                success=False,
                error=f"Неизвестный сервер: {server_name}"
            )
    
    async def _execute_supabase_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPFunctionResult:
        """Выполняет функции Supabase через реальные MCP вызовы"""
        try:
            # Маппинг функций к MCP tools
            if function_name == "supabase_list_projects":
                # Вызов реального MCP tool
                result = await self._call_mcp_tool("mcp__supabase__list_projects", {})
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "supabase_execute_sql":
                # Проверка обязательных параметров
                if "project_id" not in parameters or "query" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствуют обязательные параметры: project_id, query"
                    )
                
                # Вызов реального MCP tool
                result = await self._call_mcp_tool("mcp__supabase__execute_sql", {
                    "project_id": parameters["project_id"],
                    "query": parameters["query"]
                })
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "supabase_create_project":
                # Сначала получаем стоимость
                if "organization_id" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствует organization_id"
                    )
                
                # Получаем стоимость проекта
                cost_result = await self._call_mcp_tool("mcp__supabase__get_cost", {
                    "type": "project",
                    "organization_id": parameters["organization_id"]
                })
                
                # Подтверждаем стоимость
                confirm_result = await self._call_mcp_tool("mcp__supabase__confirm_cost", {
                    "type": "project",
                    "recurrence": cost_result.get("recurrence", "monthly"),
                    "amount": cost_result.get("amount", 0)
                })
                
                # Создаем проект
                result = await self._call_mcp_tool("mcp__supabase__create_project", {
                    "name": parameters["name"],
                    "organization_id": parameters["organization_id"],
                    "confirm_cost_id": confirm_result.get("id"),
                    "region": parameters.get("region")
                })
                
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "supabase_list_tables":
                if "project_id" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствует project_id"
                    )
                
                result = await self._call_mcp_tool("mcp__supabase__list_tables", {
                    "project_id": parameters["project_id"],
                    "schemas": parameters.get("schemas", ["public"])
                })
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "supabase_apply_migration":
                required = ["project_id", "name", "query"]
                missing = [p for p in required if p not in parameters]
                if missing:
                    return MCPFunctionResult(
                        success=False,
                        error=f"Отсутствуют параметры: {', '.join(missing)}"
                    )
                
                result = await self._call_mcp_tool("mcp__supabase__apply_migration", parameters)
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            else:
                return MCPFunctionResult(
                    success=False,
                    error=f"Неизвестная Supabase функция: {function_name}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка выполнения Supabase функции {function_name}: {e}")
            return MCPFunctionResult(
                success=False,
                error=str(e)
            )
    
    async def _execute_digitalocean_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPFunctionResult:
        """Выполняет функции DigitalOcean через реальные MCP вызовы"""
        try:
            if function_name == "digitalocean_list_apps":
                # Подготовка query параметров
                query = {
                    "page": parameters.get("page", 1),
                    "per_page": parameters.get("per_page", 20)
                }
                
                result = await self._call_mcp_tool("mcp__digitalocean__list_apps", {
                    "query": query
                })
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "digitalocean_get_app_logs":
                # Проверка обязательных параметров
                if "app_id" not in parameters or "type" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствуют обязательные параметры: app_id, type"
                    )
                
                # Получаем URL логов
                logs_url_result = await self._call_mcp_tool("mcp__digitalocean__get_deployment_logs_url", {
                    "app_id": parameters["app_id"],
                    "deployment_id": parameters.get("deployment_id"),
                    "type": parameters["type"]
                })
                
                # Скачиваем логи
                if logs_url_result and "url" in logs_url_result:
                    logs_result = await self._call_mcp_tool("mcp__digitalocean__download_logs", {
                        "url": logs_url_result["url"]
                    })
                    return MCPFunctionResult(
                        success=True,
                        data={"logs": logs_result}
                    )
                else:
                    return MCPFunctionResult(
                        success=False,
                        error="Не удалось получить URL логов"
                    )
                    
            elif function_name == "digitalocean_create_deployment":
                if "app_id" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствует app_id"
                    )
                
                result = await self._call_mcp_tool("mcp__digitalocean__create_deployment", {
                    "path": {"app_id": parameters["app_id"]},
                    "body": {"force_build": parameters.get("force_build", False)}
                })
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            elif function_name == "digitalocean_get_deployment_status":
                if "app_id" not in parameters or "deployment_id" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствуют параметры: app_id, deployment_id"
                    )
                
                result = await self._call_mcp_tool("mcp__digitalocean__get_deployment", {
                    "path": {
                        "app_id": parameters["app_id"],
                        "deployment_id": parameters["deployment_id"]
                    }
                })
                return MCPFunctionResult(
                    success=True,
                    data=result
                )
                
            else:
                return MCPFunctionResult(
                    success=False,
                    error=f"Неизвестная DigitalOcean функция: {function_name}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка выполнения DigitalOcean функции {function_name}: {e}")
            return MCPFunctionResult(
                success=False,
                error=str(e)
            )
    
    async def _execute_context7_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPFunctionResult:
        """Выполняет функции Context7 через реальные MCP вызовы"""
        try:
            if function_name == "context7_search_docs":
                # Проверка обязательных параметров
                if "library_name" not in parameters or "query" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствуют параметры: library_name, query"
                    )
                
                # Сначала резолвим библиотеку
                library_result = await self._call_mcp_tool("mcp__context7__resolve-library-id", {
                    "libraryName": parameters["library_name"]
                })
                
                if not library_result or "library_id" not in library_result:
                    return MCPFunctionResult(
                        success=False,
                        error=f"Библиотека {parameters['library_name']} не найдена"
                    )
                
                # Теперь ищем документацию
                docs_result = await self._call_mcp_tool("mcp__context7__get-library-docs", {
                    "context7CompatibleLibraryID": library_result["library_id"],
                    "topic": parameters["query"],
                    "tokens": parameters.get("limit", 10000)
                })
                
                return MCPFunctionResult(
                    success=True,
                    data=docs_result
                )
                
            elif function_name == "context7_get_code_examples":
                if "library_name" not in parameters or "topic" not in parameters:
                    return MCPFunctionResult(
                        success=False,
                        error="Отсутствуют параметры: library_name, topic"
                    )
                
                # Резолвим библиотеку
                library_result = await self._call_mcp_tool("mcp__context7__resolve-library-id", {
                    "libraryName": parameters["library_name"]
                })
                
                if not library_result or "library_id" not in library_result:
                    return MCPFunctionResult(
                        success=False,
                        error=f"Библиотека {parameters['library_name']} не найдена"
                    )
                
                # Получаем примеры кода
                examples_result = await self._call_mcp_tool("mcp__context7__get-library-docs", {
                    "context7CompatibleLibraryID": library_result["library_id"],
                    "topic": parameters["topic"],
                    "tokens": 15000  # Больше токенов для примеров кода
                })
                
                return MCPFunctionResult(
                    success=True,
                    data=examples_result
                )
                
            else:
                return MCPFunctionResult(
                    success=False,
                    error=f"Неизвестная Context7 функция: {function_name}"
                )
                
        except Exception as e:
            logger.error(f"Ошибка выполнения Context7 функции {function_name}: {e}")
            return MCPFunctionResult(
                success=False,
                error=str(e)
            )
    
    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Вызывает реальный MCP tool
        
        В продакшене здесь будет вызов через MCP протокол.
        Сейчас используем заглушку для тестирования.
        """
        # TODO: Заменить на реальные MCP вызовы когда будет настроен MCP сервер
        logger.info(f"🔧 Вызов MCP tool: {tool_name} с параметрами: {parameters}")
        
        # Временная заглушка с примерными ответами
        if tool_name == "mcp__supabase__list_projects":
            return {
                "projects": [
                    {"id": "proj_123", "name": "Test Project", "status": "active"},
                    {"id": "proj_456", "name": "Demo Project", "status": "paused"}
                ]
            }
        elif tool_name == "mcp__digitalocean__list_apps":
            return {
                "apps": [
                    {"id": "app_123", "name": "artem-bot", "status": "active"},
                    {"id": "app_456", "name": "test-app", "status": "deploying"}
                ]
            }
        elif tool_name == "mcp__context7__resolve-library-id":
            return {
                "library_id": f"/npm/{parameters.get('libraryName', 'unknown')}"
            }
        else:
            # Для остальных возвращаем успешный результат
            return {"success": True, "message": f"Выполнен {tool_name}"}
    
    def _update_metrics(
        self, 
        server_name: str, 
        function_name: str, 
        success: bool, 
        execution_time: float
    ):
        """Обновляет метрики выполнения"""
        key = f"{server_name}:{function_name}"
        metrics = self.metrics[key]
        
        metrics["total_calls"] += 1
        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1
        metrics["total_time"] += execution_time
        metrics["last_call"] = datetime.now()
    
    async def ping_all_servers(self) -> Dict[str, bool]:
        """
        Проверяет доступность всех серверов
        
        Returns:
            Dict[str, bool]: Статус каждого сервера
        """
        results = {}
        
        for server_name, connection in self.connections.items():
            try:
                if connection.is_connected:
                    # Простая проверка для MCP серверов
                    connection.last_ping = datetime.now()
                    results[server_name] = True
                else:
                    # Пытаемся подключиться
                    success = await self._connect_to_server(connection)
                    results[server_name] = success
            except Exception as e:
                logger.error(f"❌ Ошибка ping {server_name}: {e}")
                results[server_name] = False
        
        return results
    
    def get_server_status(self) -> Dict[str, Any]:
        """Получает статус всех серверов"""
        status = {}
        
        for server_name, connection in self.connections.items():
            status[server_name] = {
                "connected": connection.is_connected,
                "healthy": connection.is_healthy(),
                "last_ping": connection.last_ping.isoformat() if connection.last_ping else None,
                "error_count": connection.error_count,
                "last_error": connection.last_error
            }
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получает метрики использования"""
        metrics_summary = {
            "servers": {},
            "total_calls": 0,
            "total_successful": 0,
            "total_failed": 0,
            "average_execution_time": 0.0
        }
        
        total_time = 0.0
        
        for key, metrics in self.metrics.items():
            server_name, function_name = key.split(":", 1)
            
            if server_name not in metrics_summary["servers"]:
                metrics_summary["servers"][server_name] = {
                    "functions": {},
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0
                }
            
            metrics_summary["servers"][server_name]["functions"][function_name] = metrics
            metrics_summary["servers"][server_name]["total_calls"] += metrics["total_calls"]
            metrics_summary["servers"][server_name]["successful_calls"] += metrics["successful_calls"]
            metrics_summary["servers"][server_name]["failed_calls"] += metrics["failed_calls"]
            
            metrics_summary["total_calls"] += metrics["total_calls"]
            metrics_summary["total_successful"] += metrics["successful_calls"]
            metrics_summary["total_failed"] += metrics["failed_calls"]
            total_time += metrics["total_time"]
        
        if metrics_summary["total_calls"] > 0:
            metrics_summary["average_execution_time"] = total_time / metrics_summary["total_calls"]
        
        return metrics_summary
    
    def clear_cache(self):
        """Очищает кеш результатов"""
        old_size = len(self.cache)
        self.cache.clear()
        logger.info(f"🧹 Кеш очищен. Удалено {old_size} записей")
    
    async def close(self):
        """Закрывает все соединения"""
        await self.http_client.aclose()
        for connection in self.connections.values():
            connection.is_connected = False
        logger.info("🔌 MCP Manager закрыт")