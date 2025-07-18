"""
Model Context Protocol (MCP) модули

Обеспечивает интеграцию с внешними сервисами через MCP:
- Supabase - управление базами данных
- DigitalOcean - управление инфраструктурой  
- Context7 - поиск документации
"""

from .core.manager import MCPManager
from .core.agent import MCPAgent
from .core.exceptions import MCPError, MCPServerError, MCPAuthError

__all__ = [
    'MCPManager',
    'MCPAgent',
    'MCPError',
    'MCPServerError', 
    'MCPAuthError'
]