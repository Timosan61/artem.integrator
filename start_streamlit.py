#!/usr/bin/env python3
"""
Python wrapper для запуска Streamlit без конфликтов с Railway переменными
"""

import os
import sys
import subprocess
import re

def clean_environment():
    """Очищаем все STREAMLIT переменные из окружения"""
    print("=== Streamlit Python Wrapper Debug ===")
    
    # Показываем исходные переменные
    streamlit_vars = {k: v for k, v in os.environ.items() if k.startswith('STREAMLIT')}
    port_var = os.environ.get('PORT', 'NOT_SET')
    
    print(f"Original PORT: {port_var}")
    print(f"Original STREAMLIT vars: {streamlit_vars}")
    
    # Удаляем все STREAMLIT переменные
    vars_to_remove = [k for k in os.environ.keys() if k.startswith('STREAMLIT')]
    for var in vars_to_remove:
        print(f"Removing: {var} = {os.environ[var]}")
        del os.environ[var]
    
    # Определяем порт
    final_port = 8501
    if port_var and re.match(r'^\d+$', str(port_var)) and 1 <= int(port_var) <= 65535:
        final_port = int(port_var)
        print(f"Using Railway PORT: {final_port}")
    else:
        print(f"Using default PORT: {final_port} (Railway PORT was: {port_var})")
    
    print("Environment after cleanup:")
    remaining_vars = {k: v for k, v in os.environ.items() if 'PORT' in k or k.startswith('STREAMLIT')}
    print(f"Remaining PORT/STREAMLIT vars: {remaining_vars or 'None'}")
    print("=======================================")
    
    return final_port

def main():
    """Запуск Streamlit с очищенным окружением"""
    try:
        # Очищаем окружение и получаем порт
        port = clean_environment()
        
        # Подготавливаем команду
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            "admin/streamlit_admin.py",
            f"--server.port={port}",
            "--server.address=0.0.0.0",
            "--server.headless=true",
            "--browser.gatherUsageStats=false"
        ]
        
        print(f"Executing: {' '.join(cmd)}")
        print("=======================================")
        
        # Запускаем Streamlit
        os.execv(sys.executable, cmd)
        
    except Exception as e:
        print(f"Error starting Streamlit: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()