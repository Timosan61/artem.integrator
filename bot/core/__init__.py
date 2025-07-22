"""
Core модули бота Artem Integrator

Содержит базовые классы, интерфейсы и утилиты
"""

from .auto_admin import auto_admin_manager

# Используем простую конфигурацию для избежания проблем с импортом
try:
    from .simple_config import config
except ImportError:
    # Fallback если simple_config недоступен
    from .config import config

__all__ = ['auto_admin_manager', 'config']