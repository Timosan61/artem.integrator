"""
Новый MCP Agent с улучшенной архитектурой
Этот файл для миграции, основной mcp_agent.py будет обновлен позже
"""

from bot.mcp.core.agent import MCPAgent
from bot.core.agent import AgentFactory

# Создаем MCP агента с базовым агентом
base_agent = AgentFactory.get_agent()
mcp_agent = MCPAgent(base_agent)

# Экспортируем для использования
__all__ = ['mcp_agent']