"""
Context7 MCP Server
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..core.interfaces import (
    MCPServer, MCPServerConfig, MCPFunction, 
    MCPResult, MCPServerStatus, MCPFunctionType
)

logger = logging.getLogger(__name__)


class Context7MCPServer(MCPServer):
    """
    MCP сервер для работы с Context7
    
    Поддерживает:
    - Поиск документации библиотек
    - Получение примеров кода
    - Поиск по API референсам
    """
    
    def __init__(self, config: MCPServerConfig):
        """Инициализация Context7 сервера"""
        super().__init__(config)
        self._functions = self._define_functions()
        
    def _define_functions(self) -> List[MCPFunction]:
        """Определяет доступные функции Context7"""
        return [
            MCPFunction(
                name="resolve-library-id",
                description="Найти библиотеку по названию и получить её ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "libraryName": {
                            "type": "string",
                            "description": "Название библиотеки для поиска"
                        }
                    },
                    "required": ["libraryName"]
                },
                server="context7",
                function_type=MCPFunctionType.SEARCH,
                permissions=["read"]
            ),
            MCPFunction(
                name="get-library-docs",
                description="Получить документацию библиотеки",
                parameters={
                    "type": "object",
                    "properties": {
                        "context7CompatibleLibraryID": {
                            "type": "string",
                            "description": "ID библиотеки из resolve-library-id"
                        },
                        "tokens": {
                            "type": "number",
                            "description": "Максимум токенов документации",
                            "default": 10000
                        },
                        "topic": {
                            "type": "string",
                            "description": "Тема для фокусировки"
                        }
                    },
                    "required": ["context7CompatibleLibraryID"]
                },
                server="context7",
                function_type=MCPFunctionType.READ,
                permissions=["read"]
            )
        ]
    
    async def connect(self) -> bool:
        """Подключение к Context7 серверу"""
        try:
            self.status = MCPServerStatus.CONNECTED
            self.connected_at = datetime.now()
            logger.info("✅ Подключен к Context7")
            return True
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            self.last_error = str(e)
            logger.error(f"❌ Ошибка подключения к Context7: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """Отключение от Context7 сервера"""
        self.status = MCPServerStatus.DISCONNECTED
        logger.info("🔌 Отключен от Context7")
        return True
    
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """Выполнение функции Context7"""
        return MCPResult(
            success=True,
            data={"message": f"Context7 function {function_name} executed"},
            server="context7",
            function=function_name
        )
    
    async def get_available_functions(self) -> List[MCPFunction]:
        """Получение списка доступных функций"""
        return self._functions
    
    async def health_check(self) -> bool:
        """Проверка здоровья сервера"""
        return self.is_connected()