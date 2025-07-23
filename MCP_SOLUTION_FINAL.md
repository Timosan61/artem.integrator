# MCP Решение Конфликта SDK/Клауд ✅

## Проблема

Claude Code SDK пытался использовать Cloudflare MCP функции вместо DigitalOcean, даже когда явно просили использовать DigitalOcean.

## Причина

1. **Множественные конфигурации MCP:**
   - `/home/coder/.config/claude-code/mcp.json` - глобальная конфигурация Claude CLI
   - `/home/coder/.cursor/mcp.json` - конфигурация Cursor
   - `data/mcp-servers-local.json` - локальная конфигурация проекта

2. **Claude CLI имел зарегистрированные MCP серверы:**
   - Cloudflare
   - Supabase
   - DigitalOcean
   - GitHub
   - Context7

3. **Неправильный пакет DigitalOcean:**
   - Использовался `@anysphere/digitalocean-mcp` (не существует)
   - Правильный пакет: `@digitalocean/mcp`

## Решение

1. **Удаляем все MCP серверы из Claude CLI кроме DigitalOcean:**
   ```bash
   claude mcp remove cloudflare
   claude mcp remove supabase
   claude mcp remove github
   claude mcp remove context7
   ```

2. **Обновляем все конфигурации, оставляя только DigitalOcean:**
   ```json
   {
     "mcpServers": {
       "digitalocean": {
         "command": "npx",
         "args": ["-y", "@digitalocean/mcp"],
         "env": {
           "DIGITALOCEAN_API_TOKEN": "${DIGITALOCEAN_API_TOKEN}"
         }
       }
     }
   }
   ```

3. **Правильный пакет DigitalOcean MCP:**
   - Использовать `@digitalocean/mcp` вместо `@anysphere/digitalocean-mcp`
   - Обновить во всех конфигурациях

4. **Проверяем настройки в Клауд CLI:**
   ```bash
   claude mcp list
   ```

## Результат ✅

После выполнения этих шагов, Claude Code SDK успешно использует DigitalOcean MCP:

```
2025-07-23 03:45:36,214 - bot.services.claude_code_service - DEBUG - 📨 Получено сообщение: AssistantMessage - No role - [ToolUseBlock(id='mcp__digitalocean__list_apps_0', name='mcp__digitalocean__list_apps', input={'quer...
2025-07-23 03:45:37,151 - bot.services.claude_code_service - DEBUG - 📨 Получено сообщение: UserMessage - No role - [{'type': 'tool_result', 'content': 'No apps found', 'is_error': True, 'tool_use_id': 'mcp__digitalo...
```

SDK теперь корректно вызывает `mcp__digitalocean__list_apps` вместо TodoWrite или Cloudflare функций.

## Важные уроки

1. **Проверять глобальные настройки Claude CLI** - они имеют приоритет над локальными
2. **Убедиться в правильности имени npm пакета** - использовать `npm search` для проверки
3. **Удалить конфликтующие MCP серверы** из всех конфигураций
4. **Moonshot API работает** как альтернатива Anthropic API

## Тестирование

```bash
# Быстрый тест
python test_mcp_direct_do.py

# Результат:
# ✅ Использован инструмент: mcp__digitalocean__list_apps
# 📊 Ответ: No apps found (это нормально для пустого аккаунта)
```