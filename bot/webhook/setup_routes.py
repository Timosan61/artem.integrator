"""
Веб-интерфейс для настройки бота
"""

from fastapi import Request, Form
from fastapi.responses import HTMLResponse
import os
import json
from typing import Optional

async def setup_page(request: Request):
    """Отображает страницу настройки"""
    from ..core.config import config
    from ..core.auto_admin import auto_admin_manager
    
    # Проверяем конфигурацию
    telegram_configured = bool(config.telegram.token)
    anthropic_configured = bool(config.anthropic.api_key)
    
    # Проверяем MCP
    try:
        from ..services.claude_code_service import claude_code_service
        mcp_available = claude_code_service is not None
    except:
        mcp_available = False
    
    # Проверяем webhook
    webhook_configured = False
    webhook_url = ""
    
    # Получаем список админов
    admins = auto_admin_manager.get_all_admins()
    
    # Получаем ngrok key из env
    ngrok_key = os.getenv('NGROK_API_KEY', '')
    
    # Генерируем HTML для статусов
    telegram_status = '<span class="status-ok">✅ Настроен</span>' if telegram_configured else '<span class="status-error">❌ Не настроен</span>'
    anthropic_status = '<span class="status-ok">✅ Настроен</span>' if anthropic_configured else '<span class="status-error">❌ Не настроен</span>'
    mcp_status = '<span class="status-ok">✅ Доступен</span>' if mcp_available else '<span class="status-error">❌ Не установлен</span>'
    webhook_status = f'<span class="status-ok">{webhook_url}</span>' if webhook_configured else '<span class="status-error">❌ Не настроен</span>'
    
    # Генерируем HTML для админов
    admin_html = ""
    if admins:
        admin_items = []
        for admin in admins:
            name = admin.get('first_name', 'Без имени')
            username = f"(@{admin['username']})" if admin.get('username') else ''
            user_id = admin['user_id']
            admin_items.append(f'''
            <div class="admin-item">
                <strong>{name}</strong> {username} - ID: {user_id}
            </div>
            ''')
        admin_html = f'''
        <div class="admin-list">
            <h3>👥 Администраторы:</h3>
            {''.join(admin_items)}
        </div>
        '''
    
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка Artem Integrator</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .info {{
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .success {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .error {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .status {{
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        .status h3 {{
            margin-top: 0;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .status-ok {{
            color: #28a745;
        }}
        .status-error {{
            color: #dc3545;
        }}
        .admin-list {{
            margin-top: 20px;
        }}
        .admin-item {{
            background-color: #f8f9fa;
            padding: 10px;
            margin-bottom: 5px;
            border-radius: 5px;
        }}
        small {{
            display: block;
            margin-top: 5px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Настройка Artem Integrator</h1>
        
        <div class="info">
            <strong>Добро пожаловать!</strong><br>
            Этот интерфейс поможет вам настроить бота и активировать MCP функции.
        </div>
        
        <form method="POST" action="/setup">
            <div class="form-group">
                <label for="telegram_id">Telegram ID (необязательно):</label>
                <input type="text" id="telegram_id" name="telegram_id" placeholder="Оставьте пустым для автоматического определения">
                <small>Первый пользователь автоматически станет администратором</small>
            </div>
            
            <div class="form-group">
                <label for="ngrok_key">Ngrok API Key (необязательно):</label>
                <input type="text" id="ngrok_key" name="ngrok_key" placeholder="Для HTTPS туннеля" value="{ngrok_key}">
            </div>
            
            <button type="submit">💾 Сохранить настройки</button>
        </form>
        
        <div class="status">
            <h3>📊 Текущий статус:</h3>
            <div class="status-item">
                <span>Telegram Bot Token:</span>
                {telegram_status}
            </div>
            <div class="status-item">
                <span>Anthropic API Key:</span>
                {anthropic_status}
            </div>
            <div class="status-item">
                <span>MCP (Claude Code SDK):</span>
                {mcp_status}
            </div>
            <div class="status-item">
                <span>Webhook URL:</span>
                {webhook_status}
            </div>
        </div>
        
        {admin_html}
        
        <div class="info" style="margin-top: 30px;">
            <strong>🚀 Быстрый старт:</strong><br>
            1. Откройте Telegram и найдите вашего бота<br>
            2. Отправьте команду <code>/start</code><br>
            3. Вы автоматически станете администратором<br>
            4. Используйте <code>/help</code> для списка команд
        </div>
    </div>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

async def setup_save(
    request: Request,
    telegram_id: Optional[str] = Form(None),
    ngrok_key: Optional[str] = Form(None)
):
    """Сохраняет настройки"""
    from ..core.auto_admin import auto_admin_manager
    
    message = ""
    message_type = "success"
    
    try:
        # Сохраняем Telegram ID если указан
        if telegram_id and telegram_id.strip():
            try:
                user_id = int(telegram_id.strip())
                if auto_admin_manager.add_admin(user_id):
                    message += f"✅ Пользователь {user_id} добавлен как администратор. "
                else:
                    message += f"ℹ️ Пользователь {user_id} уже является администратором. "
            except ValueError:
                message += "❌ Неверный формат Telegram ID. "
                message_type = "error"
        
        # Сохраняем Ngrok key если указан
        if ngrok_key and ngrok_key.strip():
            # Обновляем .env файл
            env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            
            lines = []
            ngrok_found = False
            
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('NGROK_API_KEY='):
                            lines.append(f'NGROK_API_KEY={ngrok_key.strip()}\n')
                            ngrok_found = True
                        else:
                            lines.append(line)
            
            if not ngrok_found:
                lines.append(f'\nNGROK_API_KEY={ngrok_key.strip()}\n')
            
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            message += "✅ Ngrok API Key сохранен. "
            os.environ['NGROK_API_KEY'] = ngrok_key.strip()
        
        if not message:
            message = "ℹ️ Нет изменений для сохранения"
            message_type = "info"
            
    except Exception as e:
        message = f"❌ Ошибка: {str(e)}"
        message_type = "error"
    
    # Возвращаем страницу с сообщением
    from ..core.config import config
    from ..core.auto_admin import auto_admin_manager
    
    # Проверяем конфигурацию
    telegram_configured = bool(config.telegram.token)
    anthropic_configured = bool(config.anthropic.api_key)
    
    # Проверяем MCP
    try:
        from ..services.claude_code_service import claude_code_service
        mcp_available = claude_code_service is not None
    except:
        mcp_available = False
    
    # Проверяем webhook
    webhook_configured = False
    webhook_url = ""
    
    # Получаем список админов
    admins = auto_admin_manager.get_all_admins()
    
    # Получаем ngrok key из env
    ngrok_key = os.getenv('NGROK_API_KEY', '')
    
    # Генерируем HTML для статусов
    telegram_status = '<span class="status-ok">✅ Настроен</span>' if telegram_configured else '<span class="status-error">❌ Не настроен</span>'
    anthropic_status = '<span class="status-ok">✅ Настроен</span>' if anthropic_configured else '<span class="status-error">❌ Не настроен</span>'
    mcp_status = '<span class="status-ok">✅ Доступен</span>' if mcp_available else '<span class="status-error">❌ Не установлен</span>'
    webhook_status = f'<span class="status-ok">{webhook_url}</span>' if webhook_configured else '<span class="status-error">❌ Не настроен</span>'
    
    # Генерируем HTML для админов
    admin_html = ""
    if admins:
        admin_items = []
        for admin in admins:
            name = admin.get('first_name', 'Без имени')
            username = f"(@{admin['username']})" if admin.get('username') else ''
            user_id = admin['user_id']
            admin_items.append(f'''
            <div class="admin-item">
                <strong>{name}</strong> {username} - ID: {user_id}
            </div>
            ''')
        admin_html = f'''
        <div class="admin-list">
            <h3>👥 Администраторы:</h3>
            {''.join(admin_items)}
        </div>
        '''
    
    # Добавляем сообщение
    message_html = ""
    if message:
        message_html = f'<div class="{message_type}">{message}</div>'
    
    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка Artem Integrator</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }}
        input[type="text"], input[type="password"] {{
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }}
        button {{
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }}
        button:hover {{
            background-color: #45a049;
        }}
        .info {{
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .success {{
            background-color: #d4edda;
            border-left: 4px solid #28a745;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .error {{
            background-color: #f8d7da;
            border-left: 4px solid #dc3545;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .status {{
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        .status h3 {{
            margin-top: 0;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .status-ok {{
            color: #28a745;
        }}
        .status-error {{
            color: #dc3545;
        }}
        .admin-list {{
            margin-top: 20px;
        }}
        .admin-item {{
            background-color: #f8f9fa;
            padding: 10px;
            margin-bottom: 5px;
            border-radius: 5px;
        }}
        small {{
            display: block;
            margin-top: 5px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Настройка Artem Integrator</h1>
        
        {message_html}
        
        <div class="info">
            <strong>Добро пожаловать!</strong><br>
            Этот интерфейс поможет вам настроить бота и активировать MCP функции.
        </div>
        
        <form method="POST" action="/setup">
            <div class="form-group">
                <label for="telegram_id">Telegram ID (необязательно):</label>
                <input type="text" id="telegram_id" name="telegram_id" placeholder="Оставьте пустым для автоматического определения">
                <small>Первый пользователь автоматически станет администратором</small>
            </div>
            
            <div class="form-group">
                <label for="ngrok_key">Ngrok API Key (необязательно):</label>
                <input type="text" id="ngrok_key" name="ngrok_key" placeholder="Для HTTPS туннеля" value="{ngrok_key}">
            </div>
            
            <button type="submit">💾 Сохранить настройки</button>
        </form>
        
        <div class="status">
            <h3>📊 Текущий статус:</h3>
            <div class="status-item">
                <span>Telegram Bot Token:</span>
                {telegram_status}
            </div>
            <div class="status-item">
                <span>Anthropic API Key:</span>
                {anthropic_status}
            </div>
            <div class="status-item">
                <span>MCP (Claude Code SDK):</span>
                {mcp_status}
            </div>
            <div class="status-item">
                <span>Webhook URL:</span>
                {webhook_status}
            </div>
        </div>
        
        {admin_html}
        
        <div class="info" style="margin-top: 30px;">
            <strong>🚀 Быстрый старт:</strong><br>
            1. Откройте Telegram и найдите вашего бота<br>
            2. Отправьте команду <code>/start</code><br>
            3. Вы автоматически станете администратором<br>
            4. Используйте <code>/help</code> для списка команд
        </div>
    </div>
</body>
</html>
"""
    
    return HTMLResponse(content=html)

def register_setup_routes(app):
    """Регистрирует маршруты настройки"""
    app.get("/setup", response_class=HTMLResponse)(setup_page)
    app.post("/setup", response_class=HTMLResponse)(setup_save)