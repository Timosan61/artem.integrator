"""
Инструменты для Intelligent Agent
"""
from .base import BaseTool, ToolMetadata
from .echo_tool import EchoTool
# MCPTool удален в Simple Agent архитектуре
# from .mcp_tool import MCPTool

__all__ = ["BaseTool", "ToolMetadata", "EchoTool"]