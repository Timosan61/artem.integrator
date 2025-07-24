"""
Обработчики webhook запросов
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.interfaces import Message, User, MessageType, UserRole
from ..core.agent import AgentFactory
from ..core.config import config

logger = logging.getLogger(__name__)

# Опциональные импорты сервисов
try:
    from voice.voice_service import VoiceService
    voice_service = VoiceService(
        telegram_bot_token=config.telegram.token,
        openai_api_key=config.openai.api_key
    )
    logger.info("✅ Voice service инициализирован")
except ImportError as e:
    voice_service = None
    logger.warning(f"⚠️ Voice service не доступен: {e}")

try:
    from ..services.social_media_service import social_media_service
except ImportError:
    social_media_service = None

try:
    from ..services.youtube_transcript_service import youtube_transcript_service
except ImportError:
    youtube_transcript_service = None

try:
    from ..services.claude_code_service import claude_code_service
except ImportError:
    claude_code_service = None

try:
    from ..services.mcp_docker_manager import mcp_docker_manager
except ImportError:
    mcp_docker_manager = None

try:
    from ..services.intelligent_agent_service import intelligent_agent_service
except ImportError:
    intelligent_agent_service = None

from ..auth import is_admin, get_user_mode
from ..core.auto_admin import auto_admin_manager


class WebhookHandler:
    """Основной обработчик webhook запросов"""
    
    def __init__(self):
        """Инициализация обработчика"""
        self.agent = AgentFactory.get_agent()
        self.update_counter = 0
        self.last_updates = []
    
    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обрабатывает входящий update от Telegram
        
        Args:
            update: Update от Telegram API
            
        Returns:
            Dict[str, Any]: Результат обработки
        """
        logger.info(f"📥 Received update: {update}")
        
        self.update_counter += 1
        update_id = update.get('update_id', self.update_counter)
        
        logger.info(f"📨 Processing update #{update_id}, total: {self.update_counter}")
        
        # Всегда сохраняем для отладки (не только в debug режиме)
        self._save_update_for_debug(update)
        logger.info(f"💾 Saved to debug. Total updates in memory: {len(self.last_updates)}")
        
        try:
            # Определяем тип update
            if 'message' in update:
                return await self._handle_message(update['message'])
            elif 'callback_query' in update:
                return await self._handle_callback_query(update['callback_query'])
            elif 'business_message' in update:
                return await self._handle_business_message(update['business_message'])
            elif 'business_connection' in update:
                return await self._handle_business_connection(update['business_connection'])
            else:
                logger.warning(f"❓ Неизвестный тип update: {list(update.keys())}")
                return {"ok": True, "description": "Unknown update type"}
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки update {update_id}: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def _handle_message(self, telegram_message: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает обычное сообщение"""
        try:
            logger.info(f"📩 Processing message: {telegram_message}")
            
            # Извлекаем данные
            user_data = telegram_message.get('from', {})
            chat_id = telegram_message.get('chat', {}).get('id')
            text = telegram_message.get('text')
            voice = telegram_message.get('voice')
            
            logger.info(f"👤 User: {user_data.get('username', 'Unknown')} ({user_data.get('id', 'Unknown')})")
            logger.info(f"💬 Text: {text}")
            logger.info(f"🎤 Voice: {bool(voice)}")
            
            # Создаем объект пользователя
            user_id = user_data.get('id')
            username = user_data.get('username')
            is_user_admin = is_admin(user_id, username)
            
            logger.info(f"🔑 User {user_id} (@{username}) admin check: {is_user_admin}")
            
            user = User(
                id=user_id,
                username=username,
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                role=UserRole.ADMIN if is_user_admin else UserRole.USER
            )
            
            logger.info(f"👤 Created user object with role: {user.role.value}")
            
            # Определяем тип сообщения
            if voice:
                message_type = MessageType.VOICE
                # Обрабатываем голос через Voice Service с MCP интеграцией
                if voice_service and config.voice.enabled:
                    mcp_result = await self._process_voice_to_mcp(voice, user.id)
                    if mcp_result and mcp_result.get('success'):
                        # Отправляем MCP результат напрямую
                        try:
                            from ..telegram_bot import bot
                            response_text = mcp_result.get('mcp_response', 'Не удалось обработать запрос')
                            logger.info(f"📤 Sending MCP voice response to {chat_id}")
                            result = bot.send_message(chat_id, response_text)
                            return {"ok": True, "response_sent": True, "message_id": result.message_id}
                        except ImportError:
                            # Fallback через requests
                            import requests
                            url = f"https://api.telegram.org/bot{config.telegram.token}/sendMessage"
                            data = {"chat_id": chat_id, "text": mcp_result.get('mcp_response', 'Ошибка обработки')}
                            resp = requests.post(url, json=data)
                            return {"ok": True, "response_sent": resp.ok}
                    else:
                        error_msg = mcp_result.get('error', 'Ошибка обработки голоса')
                        try:
                            from ..telegram_bot import bot
                            bot.send_message(chat_id, f"❌ {error_msg}")
                        except ImportError:
                            pass
                        return {"ok": True, "description": "Voice MCP processing failed"}
                else:
                    return {"ok": True, "description": "Voice service disabled"}
            elif text:
                message_type = MessageType.TEXT
            else:
                message_type = MessageType.OTHER
            
            # Создаем объект сообщения
            message = Message(
                id=telegram_message.get('message_id'),
                user=user,
                chat_id=chat_id,
                text=text,
                type=message_type,
                timestamp=datetime.fromtimestamp(telegram_message.get('date', 0)),
                metadata={"telegram_message": telegram_message}
            )
            
            # Проверяем специальные команды
            if text and text.startswith('/'):
                special_response = await self._handle_special_command(message)
                if special_response:
                    # Важно: возвращаем сразу после обработки команды
                    return special_response
            
            # Проверяем Social Media интент
            if text and social_media_service:
                social_response = await self._handle_social_media(message)
                if social_response:
                    return social_response
            
            # Проверяем доступность Intelligent Agent для админов
            if intelligent_agent_service and intelligent_agent_service.is_available() and message.user.role == UserRole.ADMIN:
                # Используем Intelligent Agent для обработки
                logger.info(f"🧠 Using Intelligent Agent for user {message.user.id}")
                response = await intelligent_agent_service.process_message(message)
            else:
                # Обрабатываем через обычного AI агента
                logger.info(f"🤖 Using standard agent for user {message.user.id}")
                response = await self.agent.process_message(message)
            
            # Отправляем ответ
            try:
                from ..telegram_bot import bot
                logger.info(f"📤 Sending response to {chat_id}: {response.text[:100]}...")
                result = bot.send_message(chat_id, response.text)
                logger.info(f"✅ Response sent successfully. Message ID: {result.message_id if hasattr(result, 'message_id') else 'Unknown'}")
                return {"ok": True, "response_sent": True, "message_id": result.message_id if hasattr(result, 'message_id') else None}
            except ImportError as e:
                logger.error(f"❌ Failed to import telegram bot: {e}", exc_info=True)
                # Fallback: используем requests для отправки
                import requests
                url = f"https://api.telegram.org/bot{config.telegram.token}/sendMessage"
                data = {"chat_id": chat_id, "text": response.text}
                try:
                    resp = requests.post(url, json=data)
                    if resp.ok:
                        logger.info(f"✅ Response sent via API")
                        return {"ok": True, "response_sent": True}
                    else:
                        logger.error(f"❌ API error: {resp.text}")
                        return {"ok": True, "response_sent": False, "error": resp.text}
                except Exception as api_error:
                    logger.error(f"❌ Failed to send via API: {api_error}")
                    return {"ok": True, "response_sent": False, "error": str(api_error)}
            except Exception as e:
                logger.error(f"❌ Failed to send response: {e}", exc_info=True)
                return {"ok": True, "response_sent": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки сообщения: {e}", exc_info=True)
            return {"ok": False, "error": str(e)}
    
    async def _handle_callback_query(self, callback_query: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает callback query"""
        # TODO: Реализовать обработку callback queries
        return {"ok": True, "description": "Callback query handled"}
    
    async def _handle_business_message(self, business_message: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает Business API сообщение"""
        # Обрабатываем как обычное сообщение, но с business_connection_id
        result = await self._handle_message(business_message)
        
        # Добавляем business_connection_id в метаданные
        if result.get('ok'):
            result['business_connection_id'] = business_message.get('business_connection_id')
        
        return result
    
    async def _handle_business_connection(self, connection: Dict[str, Any]) -> Dict[str, Any]:
        """Обрабатывает Business API connection"""
        logger.info(f"📱 Business connection update: {connection}")
        
        connection_id = connection.get('id')
        is_enabled = connection.get('is_enabled', False)
        user_data = connection.get('user', {})
        
        if is_enabled:
            logger.info(f"✅ Business connection установлено: {connection_id}")
        else:
            logger.info(f"❌ Business connection отключено: {connection_id}")
        
        return {"ok": True, "description": f"Business connection {'enabled' if is_enabled else 'disabled'}"}
    
    async def _process_voice_to_mcp(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Обрабатывает голосовое сообщение через MCP"""
        try:
            file_id = voice_data.get('file_id')
            if not file_id:
                return {"success": False, "error": "No file_id in voice data"}
            
            # Обрабатываем через Voice Service с MCP интеграцией
            result = await voice_service.process_voice_to_mcp(
                voice_data, 
                str(user_id), 
                str(voice_data.get('file_id', 'unknown'))
            )
            
            return result or {"success": False, "error": "Voice processing failed"}
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки голоса: {e}")
            return {"success": False, "error": f"Ошибка обработки голоса: {str(e)}"}
    
    async def _handle_special_command(self, message: Message) -> Optional[Dict[str, Any]]:
        """Обрабатывает специальные команды"""
        command = message.text.split()[0].lower()
        logger.info(f"🎯 Handling special command: {command} for user {message.user.id} (role: {message.user.role.value})")
        
        # Команды для всех
        if command == '/start':
            from ..telegram_bot import bot
            
            # Автоматически добавляем первого пользователя как администратора
            if auto_admin_manager.is_first_run():
                success = auto_admin_manager.add_admin(
                    message.user.id, 
                    message.user.username,
                    message.user.first_name
                )
                if success:
                    logger.info(f"✅ Первый пользователь {message.user.id} добавлен как администратор")
                    message.user.role = UserRole.ADMIN
            
            welcome_text = self._get_welcome_message(message.user)
            try:
                bot.send_message(message.chat_id, welcome_text, parse_mode='HTML')
                logger.info(f"✅ Welcome message sent to {message.chat_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send welcome message: {e}", exc_info=True)
            return {"ok": True, "command": "start"}
        
        elif command == '/help':
            from ..telegram_bot import bot
            help_text = self._get_help_message(message.user)
            try:
                bot.send_message(message.chat_id, help_text, parse_mode='HTML')
                logger.info(f"✅ Help message sent to {message.chat_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send help message: {e}", exc_info=True)
            return {"ok": True, "command": "help"}
        
        elif command == '/mcp_enable':
            # Команда для включения MCP доступа обычным пользователям
            from ..telegram_bot import bot
            if message.user.role != UserRole.ADMIN:
                success = auto_admin_manager.add_admin(
                    message.user.id,
                    message.user.username,
                    message.user.first_name
                )
                if success:
                    message.user.role = UserRole.ADMIN
                    try:
                        bot.send_message(
                            message.chat_id,
                            "✅ MCP доступ активирован! Теперь вы можете использовать:\n\n"
                            "/mcp - Общий доступ к MCP\n"
                            "/db - Работа с базами данных\n"
                            "/docs - Поиск документации\n\n"
                            "Введите /help для полного списка команд.",
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ MCP enabled for user {message.user.id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to send MCP enable message: {e}")
                else:
                    try:
                        bot.send_message(message.chat_id, "❌ Не удалось активировать MCP доступ")
                    except:
                        pass
            else:
                try:
                    bot.send_message(message.chat_id, "ℹ️ У вас уже есть MCP доступ")
                except:
                    pass
            return {"ok": True, "command": "mcp_enable"}
        
        # Админские команды
        logger.info(f"🔐 Checking admin commands. User role: {message.user.role.value}, is ADMIN: {message.user.role == UserRole.ADMIN}")
        if message.user.role == UserRole.ADMIN:
            # Команда для статуса Intelligent Agent
            if command == '/agent':
                from ..telegram_bot import bot
                if intelligent_agent_service:
                    status = intelligent_agent_service.get_status()
                    status_text = "🧠 **Intelligent Agent Status**\n\n"
                    status_text += f"Enabled: {'✅' if status['enabled'] else '❌'}\n"
                    status_text += f"Available: {'✅' if status['available'] else '❌'}\n"
                    
                    if status['tools']:
                        status_text += f"\n**Registered Tools:**\n"
                        for tool in status['tools']:
                            status_text += f"• {tool}\n"
                    
                    status_text += f"\n**Active Confirmations:** {status['active_confirmations']}"
                else:
                    status_text = "❌ Intelligent Agent Service не доступен"
                
                try:
                    bot.send_message(message.chat_id, status_text, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"❌ Failed to send agent status: {e}")
                return {"ok": True, "command": "agent"}
            
            elif command == '/clear':
                success = await self.agent.clear_user_memory(message.user.id)
                from ..telegram_bot import bot
                try:
                    if success:
                        bot.send_message(message.chat_id, "✅ Память очищена")
                    else:
                        bot.send_message(message.chat_id, "❌ Ошибка очистки памяти")
                    logger.info(f"✅ Clear memory response sent to {message.chat_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send clear memory response: {e}", exc_info=True)
                return {"ok": True, "command": "clear"}
            
            # MCP управление Docker (только для админов)
            elif mcp_docker_manager and message.text.startswith('/mcp '):
                parts = message.text.split()
                if len(parts) >= 2:
                    mcp_command = parts[1].lower()
                    server_name = parts[2] if len(parts) > 2 else None
                    
                    # Обрабатываем команды управления
                    if mcp_command in ['start', 'stop', 'restart', 'status', 'logs', 'health']:
                        return await self._handle_mcp_docker_command(
                            message, mcp_command, server_name
                        )
            
            # MCP команды через Claude Code (только для админов)
            logger.info(f"🔌 Checking MCP commands. Command: {command}, claude_code_service: {claude_code_service is not None}")
            if claude_code_service and (
                command.startswith('/mcp') or 
                command == '/db' or 
                command == '/docs' or
                message.text.startswith('/mcp ') or
                message.text.startswith('/db ') or
                message.text.startswith('/docs ')
            ):
                logger.info(f"🔌 Processing MCP command: {message.text}")
                from ..telegram_bot import bot
                
                try:
                    # Отправляем сообщение о начале обработки
                    bot.send_message(message.chat_id, "⏳ Выполняю MCP команду...")
                    
                    # Выполняем команду через Claude Code
                    result = await claude_code_service.execute_mcp_command(
                        message.text, 
                        str(message.user.id)
                    )
                    logger.info(f"🔧 MCP result: success={result.get('success')}, has_response={bool(result.get('response'))}")
                    
                    # Форматируем ответ
                    if result.get("success"):
                        response_text = result.get("response", "Команда выполнена")
                        # Ограничиваем длину сообщения
                        if len(response_text) > 4000:
                            response_text = response_text[:3997] + "..."
                    else:
                        response_text = f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}"
                    
                    # Отправляем результат
                    logger.info(f"📤 Sending MCP response to {message.chat_id}: {response_text[:100]}...")
                    bot.send_message(message.chat_id, response_text, parse_mode='Markdown')
                    logger.info(f"✅ MCP response sent to {message.chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to execute MCP command: {e}", exc_info=True)
                    try:
                        bot.send_message(
                            message.chat_id, 
                            f"❌ Ошибка выполнения MCP команды: {str(e)}"
                        )
                    except:
                        pass
                
                return {"ok": True, "command": "mcp", "mcp_command": message.text}
        
        return None
    
    async def _handle_social_media(self, message: Message) -> Optional[Dict[str, Any]]:
        """Обрабатывает Social Media запросы"""
        # Проверяем интент через детектор
        from ..services.intent_detector import IntentDetector
        detector = IntentDetector()
        intent = await detector.detect(message)
        
        if intent['type'] in ['youtube_url', 'social_media'] and message.user.role == UserRole.ADMIN:
            # Обрабатываем через Social Media Service
            result = await social_media_service.process_message(
                message.text,
                message.user.id,
                message.user.full_name
            )
            
            if result and result.get('success'):
                from ..telegram_bot import bot
                try:
                    bot.send_message(message.chat_id, result.get('response'), parse_mode='HTML')
                    logger.info(f"✅ Social media response sent to {message.chat_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send social media response: {e}", exc_info=True)
                return {"ok": True, "social_media": True}
        
        return None
    
    def _get_welcome_message(self, user: User) -> str:
        """Генерирует приветственное сообщение"""
        if user.role == UserRole.ADMIN:
            from ..auth import format_admin_welcome_message
            return format_admin_welcome_message(user.id, user.username)
        else:
            from ..auth import format_user_welcome_message
            return format_user_welcome_message(user.full_name, user.id)
    
    def _get_help_message(self, user: User) -> str:
        """Генерирует help сообщение"""
        if user.role == UserRole.ADMIN:
            mcp_section = ""
            if claude_code_service:
                mcp_section = """
<b>🔌 MCP команды:</b>
/mcp - Общий доступ к MCP
/db &lt;query&gt; - Работа с базами данных
/docs &lt;query&gt; - Поиск документации

"""
                if mcp_docker_manager:
                    mcp_section += """<b>🐳 Управление MCP серверами:</b>
/mcp status - Статус всех серверов
/mcp status &lt;server&gt; - Статус сервера
/mcp start &lt;server&gt; - Запустить сервер
/mcp stop &lt;server&gt; - Остановить сервер
/mcp restart &lt;server&gt; - Перезапустить
/mcp logs &lt;server&gt; - Просмотр логов
/mcp health - Проверка здоровья

Серверы: supabase, digitalocean, context7, cloudflare

"""
            agent_section = ""
            if intelligent_agent_service and intelligent_agent_service.is_available():
                agent_section = """<b>🧠 Intelligent Agent:</b>
/agent - Статус Intelligent Agent
• Автоматическая классификация намерений
• Интеллектуальный выбор инструментов
• Обучение на ваших предпочтениях

"""
            
            return f"""
<b>📋 Команды администратора:</b>

/help - Показать это сообщение
/clear - Очистить память бота
/youtube &lt;url&gt; - Анализ YouTube видео
/status - Статус всех сервисов
/test - Тестовый режим

{agent_section}{mcp_section}<b>🎤 Голосовые сообщения:</b>
Отправьте голосовое сообщение для транскрипции

<b>💬 Обычный чат:</b>
Просто пишите сообщения для общения с AI
"""
        else:
            mcp_info = ""
            if claude_code_service:
                mcp_info = """
<b>🔌 MCP доступ:</b>
/mcp_enable - Активировать доступ к MCP функциям

"""
            return f"""
<b>📋 Доступные команды:</b>

/help - Показать это сообщение
/start - Начать сначала

{mcp_info}<b>💬 Как использовать:</b>
Просто отправьте мне сообщение, и я отвечу!

<b>🎤 Голосовые сообщения:</b>
Вы можете отправлять голосовые сообщения - я их расшифрую
"""
    
    async def _handle_mcp_docker_command(
        self, 
        message: Message, 
        command: str, 
        server_name: Optional[str]
    ) -> Dict[str, Any]:
        """
        Обрабатывает команды управления MCP Docker
        
        Args:
            message: Сообщение
            command: Команда (start, stop, restart, status, logs, health)
            server_name: Имя сервера или None
            
        Returns:
            Dict с результатом
        """
        from ..telegram_bot import bot
        logger.info(f"🐳 MCP Docker command: {command} {server_name}")
        
        try:
            # Выполняем команду
            if command == "status":
                result = await mcp_docker_manager.get_server_status(server_name)
                
                if result["success"]:
                    if "servers" in result:
                        # Статус всех серверов
                        text = "📊 **Статус MCP серверов:**\n\n"
                        for name, status in result["servers"].items():
                            emoji = "🟢" if status["running"] else "🔴"
                            text += f"{emoji} **{name}**: {status['status']}\n"
                    else:
                        # Статус одного сервера
                        emoji = "🟢" if result["running"] else "🔴"
                        text = f"{emoji} **{result['server']}**: {result['status']}"
                else:
                    text = f"❌ Ошибка: {result['error']}"
                    
            elif command == "start":
                if not server_name:
                    text = "❌ Укажите имя сервера: /mcp start <server>"
                else:
                    result = await mcp_docker_manager.start_server(server_name)
                    text = result["message"] if result["success"] else f"❌ {result['error']}"
                    
            elif command == "stop":
                if not server_name:
                    text = "❌ Укажите имя сервера: /mcp stop <server>"
                else:
                    result = await mcp_docker_manager.stop_server(server_name)
                    text = result["message"] if result["success"] else f"❌ {result['error']}"
                    
            elif command == "restart":
                if not server_name:
                    text = "❌ Укажите имя сервера: /mcp restart <server>"
                else:
                    result = await mcp_docker_manager.restart_server(server_name)
                    text = result["message"] if result["success"] else f"❌ {result['error']}"
                    
            elif command == "logs":
                if not server_name:
                    text = "❌ Укажите имя сервера: /mcp logs <server>"
                else:
                    result = await mcp_docker_manager.get_server_logs(server_name, lines=20)
                    if result["success"]:
                        logs = result["logs"]
                        if len(logs) > 3000:
                            logs = logs[-3000:]
                        text = f"📋 **Логи {server_name}:**\n```\n{logs}\n```"
                    else:
                        text = f"❌ {result['error']}"
                        
            elif command == "health":
                result = await mcp_docker_manager.run_health_check()
                if result["success"]:
                    emoji = "✅" if result["healthy"] else "⚠️"
                    text = f"{emoji} **Health Check:**\n\n"
                    for name, health in result["servers"].items():
                        status_emoji = "🟢" if health["healthy"] else "🔴"
                        text += f"{status_emoji} **{name}**: "
                        if health.get("error"):
                            text += f"Error - {health['error']}\n"
                        else:
                            text += f"{health['status']}\n"
                else:
                    text = f"❌ {result['error']}"
            else:
                text = f"❌ Неизвестная команда: {command}"
                
            # Отправляем ответ
            bot.send_message(message.chat_id, text, parse_mode='Markdown')
            logger.info(f"✅ MCP Docker response sent")
            
            return {"ok": True, "command": f"mcp_{command}", "server": server_name}
            
        except Exception as e:
            logger.error(f"❌ Failed to handle MCP Docker command: {e}", exc_info=True)
            try:
                bot.send_message(
                    message.chat_id,
                    f"❌ Ошибка выполнения команды: {str(e)}"
                )
            except:
                pass
            return {"ok": False, "error": str(e)}
    
    def _save_update_for_debug(self, update: Dict[str, Any]):
        """Сохраняет update для отладки"""
        self.last_updates.append({
            "id": self.update_counter,
            "timestamp": datetime.now().isoformat(),
            "update": update
        })
        # Ограничиваем размер
        if len(self.last_updates) > 10:
            self.last_updates.pop(0)


# Создаем глобальный экземпляр обработчика
webhook_handler = WebhookHandler()