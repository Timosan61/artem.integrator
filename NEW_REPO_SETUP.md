# 🆕 Настройка нового репозитория для Artyom Integrator

## 📋 Шаги для создания нового репозитория

### 1. Создайте новый репозиторий на GitHub

1. Перейдите на [GitHub.com](https://github.com)
2. Нажмите **"New repository"**
3. Введите название: `artem-integrator` 
4. Описание: `Artyom Integrator - AI консультант Елена для Textile Pro`
5. Выберите **Public** или **Private**
6. **НЕ ДОБАВЛЯЙТЕ** README, .gitignore или лицензию (у нас уже есть файлы)
7. Нажмите **"Create repository"**

### 2. Подключите новый репозиторий

После создания репозитория GitHub покажет команды. Выполните:

```bash
# Перейдите в папку проекта
cd /home/coder/Desktop/2202/artem.integrator

# Добавьте новый удаленный репозиторий
git remote add origin https://github.com/[ВАШ_USERNAME]/artem-integrator.git

# Отправьте все изменения в новый репозиторий
git push -u origin main
```

### 3. Проверьте подключение

```bash
# Проверьте что удаленный репозиторий подключен правильно
git remote -v

# Должно показать:
# origin  https://github.com/[ВАШ_USERNAME]/artem-integrator.git (fetch)
# origin  https://github.com/[ВАШ_USERNAME]/artem-integrator.git (push)
```

## 🚀 После создания репозитория

### Обновите Railway проекты

1. **Основной бот:**
   - Зайдите в Railway проект `artyom-integrator-bot`
   - Settings → Connect Repo
   - Подключите новый репозиторий `artem-integrator`
   - Укажите Root Directory: `.`
   - Railway config: `railway.json`

2. **Streamlit админка:**
   - Зайдите в Railway проект `artyom-integrator-admin`  
   - Settings → Connect Repo
   - Подключите новый репозиторий `artem-integrator`
   - Укажите Root Directory: `.`
   - Railway config: `railway-streamlit.json`

### Автоматический деплой

После подключения к новому репозиторию:
- ✅ Railway будет автоматически деплоить при push в `main`
- ✅ Webhook URL обновится автоматически
- ✅ Переменные окружения останутся без изменений

## 📁 Текущее состояние проекта

В папке `/home/coder/Desktop/2202/artem.integrator` уже готовы:

- ✅ `webhook.py` - адаптирован под Елену/Textile Pro
- ✅ `admin/` - Streamlit админка обновлена
- ✅ `railway.json` + `railway-streamlit.json` - конфигурации деплоя
- ✅ `DEPLOY_GUIDE.md` - полная инструкция по деплою
- ✅ `RAILWAY_ENV_SETUP.md` - настройка переменных окружения
- ✅ `data/instruction.json` - обновленные инструкции для Елены

## 🎯 Готово к деплою!

После создания нового репозитория у вас будет полностью независимый Artyom Integrator с автоматическим деплоем на Railway.