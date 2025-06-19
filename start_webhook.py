#!/usr/bin/env python3
"""
Скрипт запуска Telegram Business Bot Webhook Server
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def main():
    """Основная функция запуска webhook сервера"""
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/webhook.log', encoding='utf-8')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Создаем директорию для логов
        os.makedirs('logs', exist_ok=True)
        
        logger.info("🚀 Запуск Textil PRO Business Bot Webhook Server")
        
        # Проверяем критически важные переменные окружения
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'WEBHOOK_SECRET_TOKEN'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют обязательные переменные окружения: {', '.join(missing_vars)}")
            logger.error("Проверьте файл .env или настройки Railway")
            sys.exit(1)
        
        logger.info("✅ Все обязательные переменные окружения настроены")
        
        # Импортируем и запускаем webhook сервер
        try:
            import uvicorn
            from bot.webhook_server import app
            
            # Определяем порт (Railway устанавливает PORT автоматически)
            port = int(os.getenv('PORT', 8000))
            host = os.getenv('HOST', '0.0.0.0')
            
            logger.info(f"🌐 Запуск сервера на {host}:{port}")
            
            # Запускаем uvicorn сервер
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
            
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта: {e}")
            logger.error("Убедитесь что все зависимости установлены: pip install -r requirements.txt")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Webhook сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())