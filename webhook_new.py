"""
🤖 Artyom Integrator Webhook Server (Refactored)

Новая архитектура webhook сервера с модульной структурой
"""

import os
import sys
import logging
import uvicorn

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Импортируем создание приложения
try:
    from bot.webhook import create_app
    from bot.core.config import config
    
    # Создаем FastAPI приложение
    app = create_app()
    
    logger.info("✅ Webhook приложение создано успешно")
    logger.info(f"🔧 Окружение: {config.environment.value}")
    logger.info(f"🔧 Debug режим: {config.debug}")
    logger.info(f"🌐 Webhook URL: {config.webhook.base_url}")
    
except Exception as e:
    logger.error(f"❌ Ошибка создания приложения: {e}", exc_info=True)
    raise


# === MAIN ===
if __name__ == "__main__":
    """Запуск webhook сервера"""
    
    # Получаем порт из конфигурации или переменных окружения
    port = config.port
    
    logger.info(f"🚀 Запуск Webhook сервера на порту {port}...")
    
    # Запускаем сервер
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info" if config.debug else "warning",
        access_log=config.debug
    )