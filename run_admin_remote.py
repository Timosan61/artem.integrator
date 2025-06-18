#!/usr/bin/env python3
"""
Скрипт запуска Streamlit админ панели для удаленного доступа
"""

import os
import sys
import subprocess
import socket

def get_server_ip():
    """Получить IP адрес сервера"""
    try:
        # Подключаемся к внешнему серверу чтобы узнать наш IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

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
    
    server_ip = get_server_ip()
    
    print("🚀 Запуск Textil PRO Bot Admin Panel (удаленный доступ)...")
    print("📝 Управление инструкциями бота через веб-интерфейс")
    print("🌐 Интерфейс будет доступен по адресам:")
    print(f"   - Локально: http://localhost:8501")
    print(f"   - Удаленно: http://{server_ip}:8501")
    print("🔐 Пароль для входа: password")
    print("-" * 60)
    print("💡 Для SSH туннелирования используйте:")
    print(f"   ssh -L 8501:localhost:8501 user@{server_ip}")
    print("-" * 60)
    
    try:
        # Запускаем Streamlit с внешним доступом
        subprocess.run([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            admin_script,
            "--server.port=8501",
            "--server.address=0.0.0.0",
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