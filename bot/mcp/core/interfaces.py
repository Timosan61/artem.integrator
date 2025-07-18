"""
Интерфейсы и базовые классы для MCP
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from enum import Enum


class MCPServerStatus(str, Enum):
    """Статусы MCP сервера"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    INITIALIZING = "initializing"


class MCPFunctionType(str, Enum):
    """Типы MCP функций"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SEARCH = "search"


@dataclass
class MCPServerConfig:
    """Конфигурация MCP сервера"""
    name: str
    display_name: str
    description: str
    enabled: bool = False
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    timeout: int = 30
    retry_count: int = 3
    cache_ttl: int = 300  # секунды


@dataclass
class MCPFunction:
    """Описание MCP функции"""
    name: str
    description: str
    parameters: Dict[str, Any]
    server: str
    function_type: MCPFunctionType
    permissions: List[str] = field(default_factory=list)
    cache_enabled: bool = True
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Конвертирует в формат OpenAI Function"""
        return {
            "name": f"mcp__{self.server}__{self.name}",
            "description": self.description,
            "parameters": self.parameters
        }
    
    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Конвертирует в формат Anthropic Tool"""
        return {
            "name": f"mcp__{self.server}__{self.name}",
            "description": self.description,
            "input_schema": self.parameters
        }


@dataclass
class MCPResult:
    """Результат выполнения MCP функции"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    server: Optional[str] = None
    function: Optional[str] = None
    execution_time: float = 0.0
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "server": self.server,
            "function": self.function,
            "execution_time": self.execution_time,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat()
        }


class MCPServer(ABC):
    """Базовый класс для MCP сервера"""
    
    def __init__(self, config: MCPServerConfig):
        """
        Инициализация сервера
        
        Args:
            config: Конфигурация сервера
        """
        self.config = config
        self.status = MCPServerStatus.DISCONNECTED
        self.last_error: Optional[str] = None
        self.connected_at: Optional[datetime] = None
        
    @abstractmethod
    async def connect(self) -> bool:
        """Подключение к серверу"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Отключение от сервера"""
        pass
    
    @abstractmethod
    async def execute_function(
        self, 
        function_name: str, 
        parameters: Dict[str, Any]
    ) -> MCPResult:
        """Выполнение функции на сервере"""
        pass
    
    @abstractmethod
    async def get_available_functions(self) -> List[MCPFunction]:
        """Получение списка доступных функций"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка здоровья сервера"""
        pass
    
    def is_connected(self) -> bool:
        """Проверка подключения"""
        return self.status == MCPServerStatus.CONNECTED
    
    def get_status_info(self) -> Dict[str, Any]:
        """Информация о статусе сервера"""
        return {
            "name": self.config.name,
            "display_name": self.config.display_name,
            "status": self.status.value,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_error": self.last_error,
            "enabled": self.config.enabled
        }