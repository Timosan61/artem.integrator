"""
Core модули бота Artem Integrator

Содержит базовые классы, интерфейсы и утилиты
"""

from .auto_admin import auto_admin_manager
from .config import config

__all__ = ['auto_admin_manager', 'config']