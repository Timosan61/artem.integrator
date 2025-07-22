# Руководство по получению API ключей для MCP

## 🚨 Критически важный ключ

### ANTHROPIC_API_KEY
**Без этого ключа MCP работает только в режиме эмуляции!**

1. Перейдите на https://console.anthropic.com
2. Войдите или создайте аккаунт
3. Перейдите в Account → API Keys
4. Нажмите "Create Key"
5. Скопируйте ключ (начинается с `sk-ant-api03-`)
6. Добавьте в `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-ваш-ключ-здесь
   ```

## 🔧 Ключи для MCP серверов

### DIGITALOCEAN_API_TOKEN
1. Войдите в https://cloud.digitalocean.com
2. Перейдите в API → Tokens/Keys
3. Нажмите "Generate New Token"
4. Дайте имя токену и выберите права (Read + Write)
5. Скопируйте токен (начинается с `dop_v1_`)
6. Добавьте в `.env`:
   ```bash
   DIGITALOCEAN_API_TOKEN=dop_v1_ваш-токен-здесь
   ```

### SUPABASE_SERVICE_ROLE_KEY
1. Войдите в https://app.supabase.com
2. Выберите ваш проект
3. Перейдите в Settings → API
4. Скопируйте:
   - Project URL → `SUPABASE_URL`
   - service_role key → `SUPABASE_SERVICE_ROLE_KEY`
5. Добавьте в `.env`:
   ```bash
   SUPABASE_URL=https://ваш-проект.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

### CONTEXT7_API_KEY (опционально)
1. Зарегистрируйтесь на https://context7.com
2. Получите API ключ в личном кабинете
3. Добавьте в `.env`:
   ```bash
   CONTEXT7_API_KEY=ваш-ключ-context7
   ```

### CLOUDFLARE_API_TOKEN (опционально)
1. Войдите в https://dash.cloudflare.com
2. Перейдите в My Profile → API Tokens
3. Нажмите "Create Token"
4. Используйте шаблон или создайте Custom token
5. Скопируйте Account ID из правой панели
6. Добавьте в `.env`:
   ```bash
   CLOUDFLARE_API_TOKEN=ваш-токен-cloudflare
   CLOUDFLARE_ACCOUNT_ID=ваш-account-id
   ```

## 🧪 Проверка работы

После добавления ключей проверьте работу:

```bash
# Простой тест
python test_mcp_simple.py

# Полный тест
python test_local_mcp_integration.py
```

## ⚠️ Важные замечания

1. **Никогда не коммитьте `.env` файл с реальными ключами!**
2. Используйте `.env.example` как шаблон
3. Храните ключи в безопасном месте
4. Для production используйте переменные окружения сервера

## 📊 Приоритет ключей

1. **ANTHROPIC_API_KEY** - без него ничего не работает
2. **DIGITALOCEAN_API_TOKEN** - для управления инфраструктурой
3. **SUPABASE_*** - для работы с базами данных
4. **CONTEXT7_API_KEY** - для поиска документации
5. **CLOUDFLARE_*** - для Workers и CDN