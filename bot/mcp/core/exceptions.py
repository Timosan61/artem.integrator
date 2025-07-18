"""
Исключения для MCP модулей
"""

from typing import Optional


class MCPError(Exception):
    """Базовое исключение для MCP"""
    pass


class MCPServerError(MCPError):
    """Ошибка MCP сервера"""
    def __init__(self, server: str, message: str, code: Optional[int] = None):
        self.server = server
        self.code = code
        super().__init__(f"[{server}] {message}" + (f" (код: {code})" if code else ""))


class MCPAuthError(MCPError):
    """Ошибка авторизации MCP"""
    def __init__(self, server: str, message: str = "Unauthorized"):
        self.server = server
        super().__init__(f"[{server}] Ошибка авторизации: {message}")


class MCPConnectionError(MCPError):
    """Ошибка подключения к MCP серверу"""
    def __init__(self, server: str, message: str):
        self.server = server
        super().__init__(f"[{server}] Ошибка подключения: {message}")


class MCPFunctionError(MCPError):
    """Ошибка выполнения MCP функции"""
    def __init__(self, server: str, function: str, message: str):
        self.server = server
        self.function = function
        super().__init__(f"[{server}:{function}] {message}")


class MCPTimeoutError(MCPError):
    """Таймаут при работе с MCP"""
    def __init__(self, server: str, timeout: int):
        self.server = server
        self.timeout = timeout
        super().__init__(f"[{server}] Таймаут операции ({timeout}с)")


class MCPValidationError(MCPError):
    """Ошибка валидации данных MCP"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.field = field
        if field:
            super().__init__(f"Ошибка валидации поля '{field}': {message}")
        else:
            super().__init__(f"Ошибка валидации: {message}")