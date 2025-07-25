#!/usr/bin/env python3
"""
Точка входа для Streamlit приложения
Запускает админ панель Artyom Integrator
"""

import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Запускаем админку
if __name__ == "__main__":
    # Импортируем и запускаем главную функцию админки
    from admin.streamlit_admin import main
    main()