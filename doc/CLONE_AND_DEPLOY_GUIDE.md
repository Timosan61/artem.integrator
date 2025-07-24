# 🔄 Полное руководство по клонированию и деплою Artyom Integrator

## 📋 Обзор: Что вы получите

После выполнения всех шагов у вас будет:
- 🤖 **Telegram бот-консультант** с AI (как Елена из Textile Pro)
- 🌐 **Webhook сервер** на Railway с автоматическим деплоем
- 📊 **Streamlit админка** для управления ботом
- 🔄 **Автообновление** при изменениях в GitHub
- 💬 **Business API** - бот отвечает от вашего имени

---

## 🚀 Пошаговое руководство

### ШАГ 1: Подготовка Telegram бота

#### 1.1 Создайте бота через @BotFather
```
1. Откройте Telegram, найдите @BotFather
2. Отправьте команду: /newbot
3. Введите название: "Ваш Консультант Бот"
4. Введите username: your_consultant_bot
5. Сохраните токен: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

#### 1.2 Настройте Telegram Business (для Premium аккаунта)
```
1. Settings → Business → Chatbots
2. Найдите вашего бота
3. Включите "Reply to messages"
4. Бот будет отвечать от вашего имени
```

### ШАГ 2: Получение API ключей

#### 2.1 OpenAI API Key
```
1. Перейдите на https://platform.openai.com
2. Создайте аккаунт или войдите
3. API Keys → Create new secret key
4. Сохраните ключ: sk-proj-...
```

#### 2.2 Zep API Key (опционально, для памяти)
```
1. Перейдите на https://www.getzep.com
2. Создайте аккаунт
3. Получите API ключ
4. Сохраните ключ: z_...
```

### ШАГ 3: Клонирование и настройка кода

#### 3.1 Форк репозитория
```bash
1. Перейдите на https://github.com/Timosan61/artem.integrator
2. Нажмите "Fork" в правом верхнем углу
3. Выберите ваш аккаунт
4. Репозиторий будет скопирован в ваш аккаунт
```

#### 3.2 Клонирование на локальную машину
```bash
# Замените YOUR_USERNAME на ваш GitHub username
git clone https://github.com/YOUR_USERNAME/artem.integrator.git
cd artem.integrator
```

#### 3.3 Настройка под ваш бизнес
Отредактируйте файл `data/instruction.json`:

```json
{
  "system_instruction": "Замените на описание ВАШЕЙ компании и услуг",
  "welcome_message": "Добрый день! Меня зовут [ИМЯ], я менеджер компании [НАЗВАНИЕ]👋 Какой у вас вопрос?",
  "last_updated": "2025-07-15T12:00:00.000000"
}
```

#### 3.4 Обновите URL в коде (важно!)
В файлах `admin/deploy_integration.py` и `admin/streamlit_admin.py` замените:
```python
# Найдите строки с URL и замените на ваш будущий Railway URL
"https://web-production-84d8.up.railway.app/"
# На что-то вроде:
"https://your-bot-production-abcd.up.railway.app/"
```

### ШАГ 4: Деплой основного бота на Railway

#### 4.1 Создайте аккаунт Railway
```
1. Перейдите на https://railway.app
2. Войдите через GitHub
3. Подтвердите доступ к репозиториям
```

#### 4.2 Создайте проект для основного бота
```
1. Dashboard → "New Project"
2. "Deploy from GitHub repo"
3. Выберите ваш форк: your-username/artem.integrator
4. Название сервиса: "your-bot-main"
5. Дождитесь первого деплоя
```

#### 4.3 Настройте переменные окружения
Railway Dashboard → ваш проект → Variables:

```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
WEBHOOK_SECRET_TOKEN=your_bot_secret_2025
BOT_USERNAME=your_consultant_bot
OPENAI_API_KEY=sk-proj-...
ZEP_API_KEY=z_... (опционально)
```

#### 4.4 Получите Railway URL
```
1. В Railway Dashboard найдите ваш сервис
2. Скопируйте публичный URL (например: https://your-bot-production-abcd.up.railway.app)
3. Сохраните этот URL - он понадобится дальше
```

### ШАГ 5: Исправление URL в коде

#### 5.1 Обновите URL в админке
Отредактируйте файлы:
- `admin/deploy_integration.py` (строки ~208, ~213)
- `admin/streamlit_admin.py` (строки ~79, ~96)

Замените `https://web-production-84d8.up.railway.app/` на ваш реальный Railway URL.

#### 5.2 Зафиксируйте изменения
```bash
git add .
git commit -m "Настройка под мой бизнес и исправление URL

- Обновлены инструкции в data/instruction.json
- Исправлены URL в админке под мой Railway домен
- Готов к деплою

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

### ШАГ 6: Деплой Streamlit админки

#### 6.1 Создайте аккаунт Streamlit Cloud
```
1. Перейдите на https://streamlit.io
2. "Sign up" → "Continue with GitHub"
3. Подтвердите доступ к репозиториям
```

#### 6.2 Создайте Streamlit приложение
```
1. Streamlit Cloud Dashboard → "New app"
2. Repository: your-username/artem.integrator
3. Branch: main
4. Main file path: start_streamlit.py
5. App URL: выберите доступное имя (например: your-bot-admin)
```

#### 6.3 Настройте Secrets для Streamlit
В настройках Streamlit приложения → Advanced settings → Secrets:

```toml
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
BOT_USERNAME = "your_consultant_bot"
OPENAI_API_KEY = "sk-proj-..."
ZEP_API_KEY = "z_..."
GITHUB_TOKEN = "ghp_..." # Создайте Personal Access Token на GitHub
GITHUB_OWNER = "your-username"
GITHUB_REPO = "artem.integrator"
ADMIN_PASSWORD = "your_secure_admin_password"
```

### ШАГ 7: Установка webhook

#### 7.1 Для локальной разработки (Cloudflare Tunnel)
```bash
# Установите cloudflared
curl -L -o cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64
chmod +x cloudflared

# Запустите туннель
./cloudflared tunnel --url http://localhost:8000

# Установите webhook через полученный URL
curl -X POST https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-tunnel.trycloudflare.com/webhook",
    "secret_token": "your_secret_token"
  }'
```

#### 7.2 Для production (Railway)
Перейдите по ссылке (замените на ваш Railway URL):
```
https://your-bot-production-abcd.up.railway.app/webhook/set
```

#### 7.3 Проверка статуса
```
https://your-bot-production-abcd.up.railway.app/
```
Должно показать: `"status": "🟢 ONLINE"`

### ШАГ 8: Тестирование

#### 8.1 Проверьте основного бота
```
1. Откройте Telegram
2. Найдите вашего бота @your_consultant_bot
3. Отправьте /start
4. Должно прийти приветствие от вашего консультанта
5. Задайте вопрос - должен прийти AI ответ
```

#### 8.2 Проверьте админку
```
1. Откройте https://your-bot-admin.streamlit.app
2. Введите пароль админки
3. Должно показать "✅ Бот онлайн"
4. Попробуйте функции проверки промпта
```

#### 8.3 Проверьте Business API (если есть Premium)
```
1. Напишите боту в личные сообщения (не через бота)
2. Бот должен ответить от вашего имени
3. В админке можно посмотреть статистику
```

---

## 🔧 Настройка автоматического деплоя

### GitHub Webhook уже настроен!
- ✅ Railway автоматически перебирает при push в main
- ✅ Streamlit автоматически обновляется при push в main
- ✅ Изменения в коде сразу попадают в продакшн

### Правила обновлений (из CLAUDE.md):
```bash
# При любых изменениях:
git add .
git commit -m "Описание изменений

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

---

## 📋 Контрольный список

### Обязательные шаги:
- [ ] Создан Telegram бот через @BotFather
- [ ] Получены API ключи (OpenAI, Zep)
- [ ] Форкнут репозиторий artem.integrator
- [ ] Настроены инструкции в data/instruction.json
- [ ] Создан Railway проект для основного бота
- [ ] Настроены переменные окружения в Railway
- [ ] Получен Railway URL и исправлен в коде
- [ ] Создано Streamlit приложение
- [ ] Настроены Secrets в Streamlit
- [ ] Установлен webhook
- [ ] Протестирован основной функционал

### Опциональные шаги:
- [ ] Настроен Telegram Business API
- [ ] Настроен Zep для памяти диалогов
- [ ] Кастомизированы сообщения под ваш бизнес
- [ ] Добавлены дополнительные функции

---

## 🆘 Решение проблем

### Бот не отвечает:
1. Проверьте переменные окружения в Railway
2. Проверьте логи в Railway Dashboard
3. Убедитесь что webhook установлен: `/webhook/info`
4. Переустановите webhook: `/webhook/set`

### Админка показывает "Бот недоступен":
1. Проверьте Railway URL в коде админки
2. Убедитесь что основной бот запущен
3. Проверьте Secrets в Streamlit

### Ошибки AI:
1. Проверьте OPENAI_API_KEY
2. Убедитесь что у вас есть баланс на OpenAI
3. Проверьте endpoint `/debug/prompt`

---

## 🎯 Что дальше?

После успешного деплоя вы можете:

1. **Кастомизировать инструкции** через админку Streamlit
2. **Добавить свои функции** в код бота
3. **Настроить интеграции** с вашими системами
4. **Масштабировать** на несколько ботов
5. **Мониторить** работу через Railway и Streamlit

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте все шаги из этого руководства
2. Изучите файлы DEPLOY_GUIDE.md и RAILWAY_ENV_SETUP.md
3. Посмотрите логи в Railway Dashboard
4. Проверьте статус через endpoint `/debug/last-updates`

**Удачного деплоя!** 🚀