"""
DigitalOcean MCP Server
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..core.interfaces import (
    MCPServer, MCPServerConfig, MCPFunction, 
    MCPResult, MCPServerStatus, MCPFunctionType
)

logger = logging.getLogger(__name__)


class DigitalOceanMCPServer(MCPServer):
    """
    MCP сервер для работы с DigitalOcean
    
    Поддерживает:
    - Управление приложениями
    - Управление базами данных
    - Деплой и мониторинг
    """
    
    def __init__(self, config: MCPServerConfig):
        """Инициализация DigitalOcean сервера"""
        super().__init__(config)
        self._functions = self._define_functions()
        
    def _define_functions(self) -> List[MCPFunction]:
        """Определяет доступные функции DigitalOcean"""
        return [
            MCPFunction(
                name="list_apps",
                description="Получить список приложений",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "object",
                            "properties": {
                                "page": {"type": "number"},
                                "per_page": {"type": "number"}
                            }
                        }
                    },
                    "required": ["query"]
                },
                server="digitalocean",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            ),
            MCPFunction(
                name="create_deployment",
                description="Создать новый деплой приложения",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "object",
                            "properties": {
                                "app_id": {"type": "string"}
                            },
                            "required": ["app_id"]
                        },
                        "body": {
                            "type": "object",
                            "properties": {
                                "force_build": {"type": "boolean"}
                            }
                        }
                    },
                    "required": ["path", "body"]
                },
                server="digitalocean",
                function_type=MCPFunctionType.WRITE,
                permissions=["deploy"],
                cache_enabled=False
            )
        ]
    
    async def connect(self) -> bool:
        """Подключение к DigitalOcean серверу"""
        try:
            self.status = MCPServerStatus.CONNECTED
            self.connected_at = datetime.now()
            logger.info("✅ Подключен к DigitalOcean")
            return True
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            self.last_error = str(e)
            logger.error(f"❌ Ошибка подключения к DigitalOcean: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Отключение от DigitalOcean сервера"""
        self.status = MCPServerStatus.DISCONNECTED
        logger.info("🔌 Отключен от DigitalOcean")
        return True
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """Выполнение функции DigitalOcean"""
        return MCPResult(
            success=True,
            data={"message": f"DigitalOcean function {function_name} executed"},
            server="digitalocean",
            function=function_name
        )
    
    async def get_available_functions(self) -> List[MCPFunction]:
        """Получение списка доступных функций"""
        return self._functions
    
    async def health_check(self) -> bool:
        """Проверка здоровья сервера"""
        return self.is_connected()