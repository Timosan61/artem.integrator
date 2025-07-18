"""
Форматтеры для логов
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any
import traceback


class ColoredFormatter(logging.Formatter):
    """
    Цветной форматтер для консольного вывода
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    
    RESET = '\033[0m'
    
    # Эмодзи для уровней
    EMOJIS = {
        'DEBUG': '🐛',
        'INFO': '📝',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def __init__(self):
        super().__init__()
        self.fmt = "%(asctime)s | %(emoji)s %(levelname)-8s | %(name)-20s | %(message)s"
        self.datefmt = "%Y-%m-%d %H:%M:%S"
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога с цветом"""
        # Добавляем эмодзи
        record.emoji = self.EMOJIS.get(record.levelname, '📌')
        
        # Базовое форматирование
        log_fmt = self.fmt
        formatter = logging.Formatter(log_fmt, self.datefmt)
        formatted = formatter.format(record)
        
        # Добавляем цвет
        color = self.COLORS.get(record.levelname, '')
        if color:
            # Цветной уровень
            formatted = formatted.replace(
                record.levelname,
                f"{color}{record.levelname}{self.RESET}"
            )
            
            # Цветное сообщение для ошибок
            if record.levelname in ['ERROR', 'CRITICAL']:
                formatted = formatted.replace(
                    record.getMessage(),
                    f"{color}{record.getMessage()}{self.RESET}"
                )
        
        # Добавляем traceback если есть
        if record.exc_info:
            formatted += f"\n{color}{''.join(traceback.format_exception(*record.exc_info))}{self.RESET}"
        
        return formatted


class JSONFormatter(logging.Formatter):
    """
    JSON форматтер для production логов
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись лога в JSON"""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
        }
        
        # Добавляем дополнительные поля если есть
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
        
        if hasattr(record, 'chat_id'):
            log_data['chat_id'] = record.chat_id
        
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        
        # Добавляем информацию об исключении
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': ''.join(traceback.format_exception(*record.exc_info))
            }
        
        # Добавляем extra данные
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 
                          'funcName', 'levelname', 'levelno', 'lineno', 
                          'module', 'msecs', 'pathname', 'process', 
                          'processName', 'relativeCreated', 'thread', 
                          'threadName', 'exc_info', 'exc_text', 'stack_info',
                          'getMessage', 'message', 'emoji']:
                try:
                    # Пытаемся сериализовать в JSON
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class TelegramFormatter(logging.Formatter):
    """
    Форматтер для отправки логов в Telegram
    """
    
    EMOJIS = {
        'DEBUG': '🐛',
        'INFO': '📝',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись для Telegram"""
        emoji = self.EMOJIS.get(record.levelname, '📌')
        
        lines = [
            f"{emoji} <b>{record.levelname}</b>",
            f"📍 <b>Module:</b> {record.name}",
            f"📄 <b>File:</b> {record.filename}:{record.lineno}",
            f"🕐 <b>Time:</b> {datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"<b>Message:</b>",
            f"<code>{record.getMessage()}</code>"
        ]
        
        # Добавляем контекст если есть
        if hasattr(record, 'user_id'):
            lines.insert(4, f"👤 <b>User:</b> {record.user_id}")
        
        if hasattr(record, 'chat_id'):
            lines.insert(4, f"💬 <b>Chat:</b> {record.chat_id}")
        
        # Добавляем traceback для ошибок
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            
            lines.extend([
                "",
                "<b>Exception:</b>",
                f"<code>{exc_type.__name__}: {exc_value}</code>",
                "",
                "<b>Traceback:</b>",
                f"<pre>{''.join(tb_lines[-3:])}</pre>"  # Последние 3 строки traceback
            ])
        
        return "\n".join(lines)