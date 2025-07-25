"""
Debug endpoints для разработки и диагностики
"""

import os
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from ...core.config import config
from ..handlers import webhook_handler
from ..services import ServiceManager, DebugService

router = APIRouter()

# Включаем только в debug режиме
# Временно закомментируем для отладки
# if not config.debug:
#     router = APIRouter()  # Пустой роутер в production


@router.get("/last-updates")
async def get_last_updates():
    """Получить последние обработанные updates"""
    return {
        "total_updates": webhook_handler.update_counter,
        "last_updates": webhook_handler.last_updates,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/service-status")
async def get_service_status():
    """Получить статус всех сервисов"""
    service_manager = ServiceManager()
    return service_manager.get_detailed_status()


@router.get("/config")
async def get_config():
    """Получить текущую конфигурацию (без секретов)"""
    return config.get_safe_config()


@router.get("/logs/recent")
async def get_recent_logs(lines: int = 50):
    """Получить последние строки из лог файла"""
    debug_service = DebugService()
    return debug_service.get_recent_logs(lines)


@router.get("/memory/{user_id}")
async def get_user_memory(user_id: int):
    """Получить память пользователя"""
    from ...core.agent import AgentFactory
    agent = AgentFactory.get_agent()
    
    try:
        context = await agent.memory_manager.get_context(user_id)
        summary = await agent.memory_manager.get_session_summary(user_id)
        
        return {
            "user_id": user_id,
            "context_size": len(context),
            "context": context,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-status")
async def get_agent_status():
    """Получить статус AI агента"""
    from ...core.agent import AgentFactory
    agent = AgentFactory.get_agent()
    
    return await agent.get_agent_status()


@router.get("/test-mode-status")
async def get_test_mode_status():
    """Получить статус тестового режима"""
    debug_service = DebugService()
    return debug_service.get_test_mode_status()


@router.post("/test-mode/{action}")
async def toggle_test_mode(action: str):
    """Включить/выключить тестовый режим"""
    if action not in ["enable", "disable"]:
        raise HTTPException(status_code=400, detail="Action must be 'enable' or 'disable'")
    
    debug_service = DebugService()
    result = debug_service.set_test_mode(action == "enable")
    
    return result


@router.get("/environment")
async def get_environment():
    """Получить информацию об окружении"""
    return {
        "environment": config.environment.value,
        "debug": config.debug,
        "python_version": os.sys.version,
        "working_directory": os.getcwd(),
        "env_vars": {
            key: "***" if any(secret in key.lower() for secret in ["key", "token", "secret", "password"]) else value
            for key, value in os.environ.items()
            if key.startswith("BOT_") or key.startswith("TELEGRAM_") or key.startswith("OPENAI_")
        }
    }


@router.post("/clear-cache")
async def clear_cache():
    """Очистить все кеши"""
    from ...core.utils import CacheUtils
    CacheUtils.clear_all()
    
    return {"status": "Cache cleared", "timestamp": datetime.now().isoformat()}


@router.post("/test-send-message")
async def test_send_message(chat_id: int, text: str):
    """Тестовая отправка сообщения через бота"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        from ...telegram_bot import bot
        logger.info(f"📤 Attempting to send message to {chat_id}: {text}")
        
        # Проверяем, что бот инициализирован
        logger.info(f"🤖 Bot token exists: {bool(bot.token)}")
        logger.info(f"🤖 Bot token (masked): {bot.token[:10]}...{bot.token[-5:] if bot.token else 'None'}")
        
        # Пытаемся отправить сообщение
        result = bot.send_message(chat_id, text)
        
        logger.info(f"✅ Message sent successfully: {result}")
        return {
            "success": True,
            "message_id": result.message_id if hasattr(result, 'message_id') else None,
            "chat_id": chat_id,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to send message: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "chat_id": chat_id,
            "text": text,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/mcp-status")
async def mcp_status():
    """Получить статус всех MCP серверов"""
    from ..handlers import webhook_handler
    
    if not webhook_handler.mcp_manager:
        return {
            "error": "MCP Manager не инициализирован",
            "mcp_enabled": config.mcp.enabled
        }
    
    # Получаем статус серверов
    server_status = webhook_handler.mcp_manager.get_server_status()
    
    # Получаем метрики
    metrics = webhook_handler.mcp_manager.get_metrics()
    
    # Статус MCP Agent
    mcp_agent_status = {}
    if webhook_handler.mcp_agent:
        mcp_agent_status = webhook_handler.mcp_agent.get_mcp_status()
    
    return {
        "mcp_enabled": config.mcp.enabled,
        "servers": server_status,
        "metrics": metrics,
        "mcp_agent": mcp_agent_status,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/mcp-ping")
async def mcp_ping():
    """Проверить доступность всех MCP серверов"""
    from ..handlers import webhook_handler
    
    if not webhook_handler.mcp_manager:
        return {
            "error": "MCP Manager не инициализирован"
        }
    
    # Пингуем все серверы
    ping_results = await webhook_handler.mcp_manager.ping_all_servers()
    
    return {
        "ping_results": ping_results,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/mcp-test")
async def mcp_test(
    service: str,
    function: str,
    parameters: dict = {}
):
    """Тестировать конкретную MCP функцию"""
    from ..handlers import webhook_handler
    
    if not webhook_handler.mcp_manager:
        return {
            "error": "MCP Manager не инициализирован"
        }
    
    # Формируем имя функции
    function_name = f"{service}_{function}"
    
    # Выполняем функцию
    result = await webhook_handler.mcp_manager.execute_function(
        function_name=function_name,
        parameters=parameters,
        user_id="debug_test"
    )
    
    return {
        "function": function_name,
        "parameters": parameters,
        "result": {
            "success": result.success,
            "data": result.data,
            "error": result.error,
            "execution_time": result.execution_time,
            "server": result.server
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/mcp-clear-cache")
async def mcp_clear_cache():
    """Очистить кеш MCP результатов"""
    from ..handlers import webhook_handler
    
    if not webhook_handler.mcp_manager:
        return {
            "error": "MCP Manager не инициализирован"
        }
    
    webhook_handler.mcp_manager.clear_cache()
    
    return {
        "success": True,
        "message": "MCP кеш очищен",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/mcp-reload-config")
async def mcp_reload_config():
    """Перезагрузить конфигурацию MCP"""
    from ..handlers import webhook_handler
    
    if webhook_handler.mcp_agent:
        webhook_handler.mcp_agent.reload_mcp_config()
        return {
            "success": True,
            "message": "MCP конфигурация перезагружена",
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "error": "MCP Agent не инициализирован"
        }


@router.get("/voice-status")  
async def voice_status():
    """Получить статус Voice Service"""
    from ...voice import voice_service
    
    return {
        "voice_enabled": config.voice.enabled,
        "voice_service_initialized": voice_service is not None,
        "voice_service_status": voice_service.get_status() if voice_service else None,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/current-prompt")
async def get_current_prompt():
    """Получить информацию о текущем промпте без аутентификации"""
    import json
    
    instruction_file = config.data_dir / "instruction.json"
    
    if not instruction_file.exists():
        return {
            "error": "Файл инструкций не найден",
            "instruction_file": str(instruction_file),
            "exists": False,
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        with open(instruction_file, 'r', encoding='utf-8') as f:
            instruction_data = json.load(f)
        
        return {
            "instruction_file": str(instruction_file),
            "exists": True,
            "last_updated": instruction_data.get("last_updated", "Неизвестно"),
            "system_instruction_length": len(instruction_data.get("system_instruction", "")),
            "welcome_message_length": len(instruction_data.get("welcome_message", "")),
            "has_system_instruction": bool(instruction_data.get("system_instruction")),
            "has_welcome_message": bool(instruction_data.get("welcome_message")),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": f"Ошибка чтения файла: {str(e)}",
            "instruction_file": str(instruction_file),
            "exists": True,
            "timestamp": datetime.now().isoformat()
        }


@router.get("/webhook-config")
async def webhook_config():
    """Диагностика конфигурации webhook"""
    from ..services import WebhookService
    
    try:
        webhook_service = WebhookService()
        
        # Получаем текущий webhook info от Telegram
        webhook_info = await webhook_service.get_webhook_info()
        
        # Собираем информацию о переменных окружения
        env_vars = {
            "WEBHOOK_URL": os.getenv('WEBHOOK_URL'),
            "BASE_URL": os.getenv('BASE_URL'),
            "RAILWAY_PUBLIC_DOMAIN": os.getenv('RAILWAY_PUBLIC_DOMAIN'),
            "TELEGRAM_WEBHOOK_SECRET": "***" if os.getenv('TELEGRAM_WEBHOOK_SECRET') else None,
            "AUTO_SETUP_WEBHOOK": os.getenv('AUTO_SETUP_WEBHOOK', 'true')
        }
        
        # Конфигурация из config
        webhook_config_info = {
            "base_url": config.webhook.base_url,
            "auto_setup": config.webhook.auto_setup,
            "secret_token": "***" if config.webhook.secret_token else None,
            "allowed_updates": config.webhook.allowed_updates,
            "max_connections": config.webhook.max_connections
        }
        
        # Вычисляемый webhook URL
        computed_webhook_url = f"{config.webhook.base_url}/webhook" if config.webhook.base_url else "INVALID"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "environment_variables": env_vars,
            "webhook_config": webhook_config_info,
            "computed_webhook_url": computed_webhook_url,
            "telegram_webhook_info": webhook_info,
            "validation": {
                "base_url_valid": bool(config.webhook.base_url and config.webhook.base_url != ""),
                "webhook_url_valid": computed_webhook_url != "INVALID" and computed_webhook_url != "/webhook",
                "telegram_webhook_set": webhook_info.get("webhook_url") != "❌ Not set" if isinstance(webhook_info, dict) else False
            }
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }