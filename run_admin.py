#!/usr/bin/env python3
"""
Скрипт запуска Streamlit админ панели для управления инструкциями бота
"""

import os
import sys
import subprocess

def main():
    # Устанавливаем путь к проекту
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # Путь к админ панели
    admin_script = os.path.join("admin", "streamlit_admin.py")
    
    if not os.path.exists(admin_script):
        print("❌ Ошибка: файл админ панели не найден!")
        print(f"Ожидается: {admin_script}")
        sys.exit(1)
    
    print("🚀 Запуск Textil PRO Bot Admin Panel...")
    print("📝 Управление инструкциями бота через веб-интерфейс")
    print("🌐 Интерфейс будет доступен по адресу: http://localhost:8501")
    print("🔐 Пароль для входа: password")
    print("-" * 50)
    
    try:
        # Запускаем Streamlit
        subprocess.run([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            admin_script,
            "--server.port=8501",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ], check=True)
    except KeyboardInterrupt:
        print("\n👋 Админ панель остановлена пользователем")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при запуске Streamlit: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Ошибка: Streamlit не установлен!")
        print("Установите зависимости: pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()