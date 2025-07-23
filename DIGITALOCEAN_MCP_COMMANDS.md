# DigitalOcean MCP - Доступные команды

## Управление приложениями (App Platform)

### Просмотр приложений
```
/mcp apps                    # Список всех приложений
/mcp app <app-id>           # Информация о конкретном приложении
```

### Создание и обновление
```
/mcp create app <spec>      # Создать новое приложение
/mcp update app <app-id> <spec>  # Обновить приложение
/mcp delete app <app-id>    # Удалить приложение
```

### Валидация
```
/mcp validate app <spec>    # Проверить спецификацию приложения
```

## Управление деплоями

### Просмотр деплоев
```
/mcp deployments <app-id>   # Список деплоев приложения
/mcp deployment <app-id> <deployment-id>  # Информация о деплое
```

### Создание и управление
```
/mcp deploy <app-id>        # Создать новый деплой
/mcp cancel deployment <app-id> <deployment-id>  # Отменить деплой
```

### Логи
```
/mcp logs <app-id> [deployment-id]  # Получить логи деплоя
```

## Откаты

```
/mcp rollback <app-id> <deployment-id>  # Откатить к деплою
/mcp validate rollback <app-id> <deployment-id>  # Проверить возможность отката
/mcp commit rollback <app-id>    # Подтвердить откат
/mcp revert rollback <app-id>    # Отменить откат
```

## Базы данных

### Просмотр БД
```
/mcp databases              # Список всех кластеров БД
/mcp database <cluster-id>  # Информация о кластере
/mcp database options       # Доступные опции для создания БД
```

### Создание БД
```
/mcp create database <engine> <name> <region> <size>  # Создать БД
```

### Управление доступом
```
/mcp database users <cluster-id>      # Список пользователей
/mcp database firewall <cluster-id>   # Правила фаервола
/mcp database cert <cluster-id>       # Получить SSL сертификат
```

## Алерты

```
/mcp alerts <app-id>        # Список алертов приложения
/mcp update alerts <app-id> <emails> <slack-webhooks>  # Обновить получателей
```

## Регионы и размеры

```
/mcp regions                # Список доступных регионов
/mcp instance-sizes         # Список размеров инстансов
/mcp instance-size <slug>   # Информация о размере
```

## Примеры использования

### Создание простого приложения
```
/mcp create app {
  "name": "my-app",
  "region": "fra1",
  "services": [{
    "name": "web",
    "github": {
      "repo": "user/repo",
      "branch": "main"
    }
  }]
}
```

### Создание PostgreSQL базы данных
```
/mcp create database pg my-database fra1 db-s-1vcpu-1gb
```

### Получение логов последнего деплоя
```
/mcp logs app-123abc
```

## Примечания

- **Проекты НЕ поддерживаются** - DigitalOcean MCP не включает функции управления проектами
- Для всех команд требуется валидный `DIGITALOCEAN_API_TOKEN`
- Спецификации приложений должны соответствовать [AppSpec формату](https://docs.digitalocean.com/products/app-platform/reference/app-spec/)
- Размеры инстансов можно получить командой `/mcp instance-sizes`