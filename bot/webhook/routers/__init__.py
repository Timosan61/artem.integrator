"""
Роутеры для webhook сервера
"""

from . import health
from . import webhook
from . import debug
from . import admin
from . import test

__all__ = ['health', 'webhook', 'debug', 'admin', 'test']