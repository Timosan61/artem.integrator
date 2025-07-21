#!/bin/bash

# Deploy через MCP DigitalOcean (альтернативный способ)

echo "🚀 Деплой Artem Integrator через MCP DigitalOcean App Platform"
echo "=============================================================="
echo ""
echo "⚠️  ВАЖНО: Для этого способа деплоя необходимо:"
echo "1. Настроенный MCP с DigitalOcean токеном"
echo "2. Публичный GitHub репозиторий"
echo "3. Запущенный локально бот с MCP"
echo ""

# Проверяем что бот запущен
if ! pgrep -f "webhook.py" > /dev/null; then
    echo "❌ Бот не запущен. Запустите его сначала:"
    echo "   python webhook.py"
    exit 1
fi

echo "✅ Бот запущен"
echo ""
echo "📋 Инструкция по деплою через MCP:"
echo ""
echo "1. Откройте Telegram и найдите вашего бота"
echo "2. Отправьте команду: /mcp apps"
echo "   Это покажет список существующих приложений"
echo ""
echo "3. Для создания нового приложения используйте естественный язык:"
echo "   'Создай новое приложение artem-integrator на DigitalOcean'"
echo ""
echo "4. Или используйте Python скрипт:"
echo "   python deploy_with_mcp.py deploy"
echo ""
echo "5. После создания приложения:"
echo "   - Настройте переменные окружения в DigitalOcean App Platform"
echo "   - Дождитесь завершения первого деплоя"
echo "   - Получите URL приложения и настройте webhook"
echo ""
echo "🔧 Альтернативный вариант - App Spec файл:"
echo "   Создайте app.yaml с конфигурацией и загрузите через DO панель"
echo ""

# Создаем app spec файл
cat > digitalocean-app-spec.yaml << 'EOF'
name: artem-integrator
region: fra
services:
  - name: web
    github:
      repo: Timosan61/artem.integrator
      branch: main
      deploy_on_push: true
    build_command: pip install -r requirements.txt
    run_command: python -m uvicorn bot.webhook:app --host 0.0.0.0 --port 8080
    environment_slug: python
    instance_size_slug: basic-xxs
    instance_count: 1
    http_port: 8080
    health_check:
      http_path: /
      period_seconds: 30
    envs:
      - key: PYTHON_VERSION
        value: "3.10"
      - key: TELEGRAM_TOKEN
        value: "${TELEGRAM_TOKEN}"
        type: SECRET
      - key: TELEGRAM_WEBHOOK_SECRET
        value: "${TELEGRAM_WEBHOOK_SECRET}"
        type: SECRET
      - key: OPENAI_API_KEY
        value: "${OPENAI_API_KEY}"
        type: SECRET
      - key: ANTHROPIC_API_KEY
        value: "${ANTHROPIC_API_KEY}"
        type: SECRET
      - key: MCP_ENABLED
        value: "true"
      - key: ANTHROPIC_ENABLED
        value: "true"
      - key: SUPABASE_ENABLED
        value: "true"
      - key: DIGITALOCEAN_ENABLED
        value: "true"
      - key: CONTEXT7_ENABLED
        value: "true"
      - key: ENVIRONMENT
        value: "production"
EOF

echo "✅ Создан файл digitalocean-app-spec.yaml"
echo ""
echo "📌 Следующие шаги:"
echo "1. Войдите в DigitalOcean: https://cloud.digitalocean.com/"
echo "2. Перейдите в App Platform"
echo "3. Создайте новое приложение из GitHub"
echo "4. Или загрузите digitalocean-app-spec.yaml"
echo ""
echo "💡 Совет: Используйте MCP команды в Telegram для управления:"
echo "   /mcp apps - список приложений"
echo "   /deploy <app-id> - запустить деплой"
echo "   /logs <app-id> - просмотр логов"