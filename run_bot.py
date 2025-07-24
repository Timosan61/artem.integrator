#!/usr/bin/env python3
"""
Скрипт запуска бота
"""

import uvicorn
from bot.webhook.app import create_app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)