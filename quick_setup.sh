#!/bin/bash

echo "🚀 Быстрая установка Streamlit в текущем окружении"
echo "=================================================="

# Проверяем, что мы в виртуальном окружении
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Виртуальное окружение активно: $VIRTUAL_ENV"
else
    echo "⚠️  Виртуальное окружение не активно"
fi

echo "📥 Установка зависимостей..."

# Устанавливаем зависимости с флагом --break-system-packages
pip install --break-system-packages streamlit==1.28.1
pip install --break-system-packages streamlit-ace==0.1.1
pip install --break-system-packages gitpython==3.1.40
pip install --break-system-packages requests==2.31.0

echo "✅ Установка завершена!"
echo ""
echo "🎯 Для запуска админ панели:"
echo "python run_admin.py"
echo ""
echo "🌐 Затем откройте: http://localhost:8501"
echo "🔐 Пароль: password"