#!/usr/bin/env python3
"""
Streamlit Admin Panel Launcher
Запускает административную панель для управления Artyom Integrator
"""

import subprocess
import sys
import os

def main():
    """Запуск Streamlit приложения"""
    print("🚀 Запуск Streamlit Admin Panel...")
    
    # Переходим в директорию проекта
    project_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_dir)
    
    # Запускаем Streamlit
    try:
        subprocess.run([
            sys.executable, 
            "-m", "streamlit", 
            "run", 
            "admin/streamlit_admin.py",
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--server.headless=true"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска Streamlit: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Streamlit Admin Panel остановлен")
        sys.exit(0)

if __name__ == "__main__":
    main()