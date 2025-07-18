"""
MCP Manager - Централизованный менеджер для управления MCP серверами
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json

from .interfaces import (
    MCPServer, MCPServerConfig, MCPFunction, 
    MCPResult, MCPServerStatus, MCPFunctionType
)
from .exceptions import (
    MCPError, MCPServerError, MCPConnectionError,
    MCPFunctionError, MCPTimeoutError
)
from .cache import MCPCache
from ..servers import get_server_class

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Централизованный менеджер для MCP серверов
    
    Функции:
    - Управление жизненным циклом серверов
    - Маршрутизация запросов
    - Кеширование результатов
    - Мониторинг и метрики
    - Обработка ошибок и повторные попытки
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера
        
        Args:
            config: Конфигурация MCP (загружается из файла если не передана)
        """
        self.config = config or self._load_config()
        self.servers: Dict[str, MCPServer] = {}
        self.cache = MCPCache()
        self.metrics = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_time": 0.0,
            "last_call": None,
            "errors": []
        })
        
        # Инициализация серверов
        self._initialize_servers()
        
        # Запуск фоновых задач
        self._background_tasks = []
        self._start_background_tasks()
        
        logger.info(f"🔌 MCP Manager инициализирован с {len(self.servers)} серверами")
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        try:
            with open('data/mcp_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("⚠️ MCP конфигурация не найдена, используем дефолтную")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки MCP конфигурации: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает дефолтную конфигурацию"""
        return {
            "mcp_enabled": True,
            "cache_ttl": 300,
            "health_check_interval": 60,
            "servers": {}
        }
    
    def _initialize_servers(self):
        """Инициализирует MCP серверы из конфигурации"""
        servers_config = self.config.get("servers", {})
        
        for server_name, server_data in servers_config.items():
            if not server_data.get("enabled", False):
                logger.info(f"⏭️ Сервер {server_name} отключен в конфигурации")
                continue
            
            try:
                # Создаем конфигурацию сервера
                config = MCPServerConfig(
                    name=server_name,
                    display_name=server_data.get("display_name", server_name),
                    description=server_data.get("description", ""),
                    enabled=True,
                    api_url=server_data.get("api_url"),
                    api_key=server_data.get("api_key"),
                    permissions=server_data.get("permissions", []),
                    timeout=server_data.get("timeout", 30),
                    retry_count=server_data.get("retry_count", 3),
                    cache_ttl=server_data.get("cache_ttl", 300)
                )
                
                # Получаем класс сервера и создаем экземпляр
                server_class = get_server_class(server_name)
                if server_class:
                    self.servers[server_name] = server_class(config)
                    logger.info(f"✅ Сервер {server_name} инициализирован")
                else:
                    logger.warning(f"⚠️ Класс сервера {server_name} не найден")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации сервера {server_name}: {e}")
    
    def _start_background_tasks(self):
        """Запускает фоновые задачи"""
        # Health check task
        if self.config.get("health_check_interval", 60) > 0:
            task = asyncio.create_task(self._health_check_loop())
            self._background_tasks.append(task)
    
    async def _health_check_loop(self):
        """Периодическая проверка здоровья серверов"""
        interval = self.config.get("health_check_interval", 60)
        
        while True:
            try:
                await asyncio.sleep(interval)
                await self.health_check_all()
            except Exception as e:
                logger.error(f"❌ Ошибка в health check цикле: {e}")
    
    async def connect_server(self, server_name: str) -> bool:
        """
        Подключает конкретный сервер
        
        Args:
            server_name: Имя сервера
            
        Returns:
            bool: Успешность подключения
        """
        if server_name not in self.servers:
            logger.error(f"❌ Сервер {server_name} не найден")
            return False
        
        server = self.servers[server_name]
        try:
            success = await server.connect()
            if success:
                logger.info(f"✅ Сервер {server_name} подключен")
            else:
                logger.warning(f"⚠️ Не удалось подключить сервер {server_name}")
            return success
        except Exception as e:
            logger.error(f"❌ Ошибка подключения сервера {server_name}: {e}")
            return False
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Подключает все включенные серверы
        
        Returns:
            Dict[str, bool]: Результаты подключения
        """
        results = {}
        connect_tasks = []
        
        for server_name in self.servers:
            task = self.connect_server(server_name)
            connect_tasks.append((server_name, task))
        
        for server_name, task in connect_tasks:
            results[server_name] = await task
        
        return results
    
    async def execute_function(
        self,
        server_name: str,
        function_name: str,
        parameters: Dict[str, Any],
        use_cache: bool = True
    ) -> MCPResult:
        """
        Выполняет функцию на MCP сервере
        
        Args:
            server_name: Имя сервера
            function_name: Имя функции
            parameters: Параметры функции
            use_cache: Использовать кеш
            
        Returns:
            MCPResult: Результат выполнения
        """
        start_time = datetime.now()
        
        # Проверяем наличие сервера
        if server_name not in self.servers:
            return MCPResult(
                success=False,
                error=f"Сервер {server_name} не найден",
                server=server_name,
                function=function_name
            )
        
        server = self.servers[server_name]
        
        # Проверяем подключение
        if not server.is_connected():
            logger.warning(f"⚠️ Сервер {server_name} не подключен, пытаемся подключить")
            connected = await self.connect_server(server_name)
            if not connected:
                return MCPResult(
                    success=False,
                    error=f"Не удалось подключиться к серверу {server_name}",
                    server=server_name,
                    function=function_name
                )
        
        # Проверяем кеш
        if use_cache:
            cache_key = self.cache.get_key(server_name, function_name, parameters)
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"📦 Использован кеш для {server_name}:{function_name}")
                cached_result.cached = True
                return cached_result
        
        # Выполняем функцию
        try:
            result = await asyncio.wait_for(
                server.execute_function(function_name, parameters),
                timeout=server.config.timeout
            )
            
            # Обновляем метрики
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_metrics(server_name, function_name, True, execution_time)
            
            # Кешируем успешный результат
            if use_cache and result.success:
                self.cache.set(
                    self.cache.get_key(server_name, function_name, parameters),
                    result,
                    ttl=server.config.cache_ttl
                )
            
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Таймаут выполнения ({server.config.timeout}с)"
            self._update_metrics(server_name, function_name, False, 
                               (datetime.now() - start_time).total_seconds(), error_msg)
            return MCPResult(
                success=False,
                error=error_msg,
                server=server_name,
                function=function_name
            )
        except Exception as e:
            error_msg = str(e)
            self._update_metrics(server_name, function_name, False,
                               (datetime.now() - start_time).total_seconds(), error_msg)
            logger.error(f"❌ Ошибка выполнения {server_name}:{function_name}: {e}")
            return MCPResult(
                success=False,
                error=error_msg,
                server=server_name,
                function=function_name
            )
    
    def _update_metrics(
        self, 
        server_name: str, 
        function_name: str, 
        success: bool, 
        execution_time: float,
        error: Optional[str] = None
    ):
        """Обновляет метрики"""
        key = f"{server_name}:{function_name}"
        metrics = self.metrics[key]
        
        metrics["total_calls"] += 1
        if success:
            metrics["successful_calls"] += 1
        else:
            metrics["failed_calls"] += 1
            if error:
                metrics["errors"].append({
                    "timestamp": datetime.now().isoformat(),
                    "error": error
                })
                # Ограничиваем количество сохраненных ошибок
                if len(metrics["errors"]) > 10:
                    metrics["errors"] = metrics["errors"][-10:]
        
        metrics["total_time"] += execution_time
        metrics["last_call"] = datetime.now().isoformat()
    
    async def get_available_functions(
        self, 
        server_name: Optional[str] = None
    ) -> List[MCPFunction]:
        """
        Получает список доступных функций
        
        Args:
            server_name: Имя сервера (если None - для всех серверов)
            
        Returns:
            List[MCPFunction]: Список функций
        """
        functions = []
        
        if server_name:
            if server_name in self.servers:
                server = self.servers[server_name]
                if server.is_connected():
                    try:
                        server_functions = await server.get_available_functions()
                        functions.extend(server_functions)
                    except Exception as e:
                        logger.error(f"❌ Ошибка получения функций {server_name}: {e}")
        else:
            # Получаем функции со всех серверов
            tasks = []
            for name, server in self.servers.items():
                if server.is_connected():
                    task = server.get_available_functions()
                    tasks.append((name, task))
            
            for name, task in tasks:
                try:
                    server_functions = await task
                    functions.extend(server_functions)
                except Exception as e:
                    logger.error(f"❌ Ошибка получения функций {name}: {e}")
        
        return functions
    
    async def health_check_all(self) -> Dict[str, bool]:
        """
        Проверяет здоровье всех серверов
        
        Returns:
            Dict[str, bool]: Результаты проверки
        """
        results = {}
        
        for server_name, server in self.servers.items():
            try:
                if server.is_connected():
                    results[server_name] = await server.health_check()
                else:
                    results[server_name] = False
            except Exception as e:
                logger.error(f"❌ Ошибка health check {server_name}: {e}")
                results[server_name] = False
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Получает статус всех серверов и метрики"""
        status = {
            "servers": {},
            "cache_stats": self.cache.get_stats(),
            "metrics_summary": self._get_metrics_summary()
        }
        
        for server_name, server in self.servers.items():
            status["servers"][server_name] = server.get_status_info()
        
        return status
    
    def _get_metrics_summary(self) -> Dict[str, Any]:
        """Получает сводку метрик"""
        total_calls = sum(m["total_calls"] for m in self.metrics.values())
        successful_calls = sum(m["successful_calls"] for m in self.metrics.values())
        failed_calls = sum(m["failed_calls"] for m in self.metrics.values())
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "failed_calls": failed_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "top_functions": self._get_top_functions(5),
            "recent_errors": self._get_recent_errors(5)
        }
    
    def _get_top_functions(self, limit: int) -> List[Dict[str, Any]]:
        """Получает топ используемых функций"""
        sorted_metrics = sorted(
            self.metrics.items(),
            key=lambda x: x[1]["total_calls"],
            reverse=True
        )[:limit]
        
        return [
            {
                "function": key,
                "calls": value["total_calls"],
                "success_rate": value["successful_calls"] / value["total_calls"] 
                                if value["total_calls"] > 0 else 0,
                "avg_time": value["total_time"] / value["total_calls"]
                           if value["total_calls"] > 0 else 0
            }
            for key, value in sorted_metrics
        ]
    
    def _get_recent_errors(self, limit: int) -> List[Dict[str, Any]]:
        """Получает последние ошибки"""
        all_errors = []
        
        for function, metrics in self.metrics.items():
            for error in metrics["errors"]:
                all_errors.append({
                    "function": function,
                    "timestamp": error["timestamp"],
                    "error": error["error"]
                })
        
        # Сортируем по времени и берем последние
        all_errors.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_errors[:limit]
    
    async def shutdown(self):
        """Корректное завершение работы менеджера"""
        logger.info("🔌 Завершение работы MCP Manager...")
        
        # Отменяем фоновые задачи
        for task in self._background_tasks:
            task.cancel()
        
        # Отключаем все серверы
        disconnect_tasks = []
        for server_name, server in self.servers.items():
            if server.is_connected():
                task = server.disconnect()
                disconnect_tasks.append((server_name, task))
        
        for server_name, task in disconnect_tasks:
            try:
                await task
                logger.info(f"✅ Сервер {server_name} отключен")
            except Exception as e:
                logger.error(f"❌ Ошибка отключения сервера {server_name}: {e}")
        
        logger.info("✅ MCP Manager завершил работу")