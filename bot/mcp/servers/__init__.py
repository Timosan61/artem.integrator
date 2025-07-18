"""
MCP серверы
"""

from typing import Type, Optional
from ..core.interfaces import MCPServer

# Импортируем конкретные реализации серверов
from .supabase import SupabaseMCPServer
from .digitalocean import DigitalOceanMCPServer
from .context7 import Context7MCPServer

# Реестр серверов
SERVER_REGISTRY = {
    "supabase": SupabaseMCPServer,
    "digitalocean": DigitalOceanMCPServer,
    "context7": Context7MCPServer
}


def get_server_class(server_name: str) -> Optional[Type[MCPServer]]:
    """
    Получает класс сервера по имени
    
    Args:
        server_name: Имя сервера
        
    Returns:
        Optional[Type[MCPServer]]: Класс сервера или None
    """
    return SERVER_REGISTRY.get(server_name.lower())


def register_server(name: str, server_class: Type[MCPServer]):
    """
    Регистрирует новый сервер
    
    Args:
        name: Имя сервера
        server_class: Класс сервера
    """
    SERVER_REGISTRY[name.lower()] = server_class


__all__ = [
    'SupabaseMCPServer',
    'DigitalOceanMCPServer',
    'Context7MCPServer',
    'get_server_class',
    'register_server'
]