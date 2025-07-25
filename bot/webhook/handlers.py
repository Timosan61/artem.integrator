"""
Обработчики webhook запросов
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from ..core.interfaces import Message, User, MessageType, UserRole
from ..core.unified_agent import unified_agent
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
    from ..services.ytdlp_service import ytdlp_service
except ImportError:
    ytdlp_service = None

try:
    from ..services.unified_mcp_service import unified_mcp_service
except ImportError:
    unified_mcp_service = None


from ..auth import is_admin, get_user_mode
from ..core.auto_admin import auto_admin_manager


def send_business_message(chat_id: int, text: str, business_connection_id: str) -> Dict[str, Any]:
    """
    Отправка сообщения через Business API используя прямой HTTP запрос
    (pyTelegramBotAPI не поддерживает business_connection_id)
    
    Args:
        chat_id: ID чата для отправки
        text: Текст сообщения
        business_connection_id: ID Business подключения
        
    Returns:
        Dict[str, Any]: Результат отправки с деталями
    """
    # Валидация входных данных
    if not chat_id:
        logger.error("❌ chat_id не может быть пустым")
        return {"success": False, "error": "Invalid chat_id", "details": "chat_id is required"}
    
    if not text or not text.strip():
        logger.error("❌ text не может быть пустым")
        return {"success": False, "error": "Invalid text", "details": "text is required and cannot be empty"}
    
    if not business_connection_id:
        logger.error("❌ business_connection_id не может быть пустым")
        return {"success": False, "error": "Invalid business_connection_id", "details": "business_connection_id is required"}
    
    # Ограничение длины сообщения
    if len(text) > 4096:
        logger.warning(f"⚠️ Сообщение слишком длинное ({len(text)} символов), обрезаю до 4096")
        text = text[:4093] + "..."
    
    url = f"https://api.telegram.org/bot{config.telegram.token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "business_connection_id": business_connection_id,
        "parse_mode": "HTML"  # Добавляем поддержку HTML форматирования
    }
    
    try:
        logger.info(f"📤 Отправляю Business сообщение: chat_id={chat_id}, connection_id={business_connection_id}, text_length={len(text)}")
        
        response = requests.post(url, json=data, timeout=15)
        result = response.json()
        
        logger.info(f"📨 Telegram API response: status={response.status_code}, ok={result.get('ok')}")
        
        if response.status_code == 200 and result.get("ok"):
            message_id = result.get('result', {}).get('message_id', 'Unknown')
            logger.info(f"✅ Business сообщение отправлено успешно: message_id={message_id}")
            return {
                "success": True, 
                "message_id": message_id,
                "api_response": result
            }
        else:
            error_code = result.get("error_code", "Unknown")
            error_description = result.get("description", "Unknown error")
            logger.error(f"❌ Telegram API ошибка: code={error_code}, description={error_description}")
            
            return {
                "success": False, 
                "error": f"Telegram API Error {error_code}",
                "details": error_description,
                "api_response": result
            }
            
    except requests.exceptions.Timeout:
        logger.error("❌ Timeout при отправке Business сообщения (15 секунд)")
        return {"success": False, "error": "Request timeout", "details": "Request took longer than 15 seconds"}
    except requests.exceptions.ConnectionError as e:
        logger.error(f"❌ Ошибка соединения с Telegram API: {e}")
        return {"success": False, "error": "Connection error", "details": str(e)}
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ HTTP ошибка при отправке Business сообщения: {e}")
        return {"success": False, "error": "HTTP error", "details": str(e)}
    except ValueError as e:
        logger.error(f"❌ Ошибка парсинга JSON ответа: {e}")
        return {"success": False, "error": "JSON parse error", "details": str(e)}
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка при отправке Business сообщения: {e}", exc_info=True)
        return {"success": False, "error": "Unexpected error", "details": str(e)}


def get_business_connections_info() -> Dict[str, Any]:
    """
    Получает информацию о Business подключениях бота
    
    Returns:
        Dict[str, Any]: Информация о подключениях
    """
    url = f"https://api.telegram.org/bot{config.telegram.token}/getBusinessConnection"
    
    try:
        logger.info("🔍 Запрашиваю информацию о Business подключениях...")
        
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if response.status_code == 200 and result.get("ok"):
            connections = result.get("result", [])
            logger.info(f"✅ Найдено {len(connections)} Business подключений")
            
            return {
                "success": True,
                "connections_count": len(connections),
                "connections": connections
            }
        else:
            error_description = result.get("description", "Unknown error")
            logger.error(f"❌ Ошибка получения Business подключений: {error_description}")
            
            return {
                "success": False,
                "error": "API Error",
                "details": error_description
            }
            
    except Exception as e:
        logger.error(f"❌ Ошибка запроса Business подключений: {e}")
        return {
            "success": False,
            "error": "Request failed",
            "details": str(e)
        }


class WebhookHandler:
    """Основной обработчик webhook запросов"""
    
    def __init__(self):
        """Инициализация обработчика"""
        self.agent = unified_agent
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
    
    async def _handle_message(self, telegram_message: Dict[str, Any], is_business: bool = False, business_connection_id: Optional[str] = None) -> Dict[str, Any]:
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
            logger.info(f"📱 Is business message: {is_business}")
            
            # Определяем тип сообщения
            if voice:
                message_type = MessageType.VOICE
                # Сначала транскрибируем голос
                if voice_service and config.voice.enabled:
                    logger.info("🎤 Транскрибируем голосовое сообщение...")
                    transcription_result = await self._process_voice_transcription(voice, user.id)
                    
                    if transcription_result and transcription_result.get('success'):
                        # Получаем транскрибированный текст
                        text = transcription_result.get('text')
                        logger.info(f"✅ Транскрипция: {text}")
                        
                        # Теперь обрабатываем как обычное текстовое сообщение
                        message_type = MessageType.TEXT
                    else:
                        error_msg = transcription_result.get('error', 'Ошибка транскрипции')
                        try:
                            from ..telegram_bot import bot
                            bot.send_message(chat_id, f"❌ {error_msg}")
                        except ImportError:
                            pass
                        return {"ok": True, "description": "Voice transcription failed"}
                else:
                    return {"ok": True, "description": "Voice service disabled"}
            elif text:
                message_type = MessageType.TEXT
            else:
                message_type = MessageType.OTHER
            
            # Создаем объект сообщения
            metadata = {"telegram_message": telegram_message}
            if business_connection_id:
                metadata["business_connection_id"] = business_connection_id
                
            message = Message(
                id=telegram_message.get('message_id'),
                user=user,
                chat_id=chat_id,
                text=text,
                type=message_type,
                timestamp=datetime.fromtimestamp(telegram_message.get('date', 0)),
                metadata=metadata,
                is_business_message=is_business
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
            
            # Обрабатываем через унифицированный агент
            logger.info(f"🔗 Processing message through UnifiedAgent")
            response = await self.agent.process_message(message)
            
            # Отправляем ответ
            if is_business and business_connection_id:
                # Для Business сообщений используем специальную функцию
                logger.info(f"📤 Sending Business response to {chat_id}: {response.text[:100]}...")
                result = send_business_message(chat_id, response.text, business_connection_id)
                
                if result.get("success"):
                    logger.info(f"✅ Business сообщение отправлено: message_id={result.get('message_id')}")
                    return {
                        "ok": True, 
                        "response_sent": True, 
                        "method": "business_api",
                        "message_id": result.get('message_id'),
                        "business_connection_id": business_connection_id
                    }
                else:
                    error_details = result.get("details", "Unknown error")
                    logger.warning(f"⚠️ Business API не сработал ({error_details}), пробуем обычную отправку...")
                    # Fallback к обычной отправке
            
            # Обычная отправка или fallback для Business
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
        logger.info(f"📱 Обработка Business сообщения: {business_message}")
        
        # Извлекаем business_connection_id
        business_connection_id = business_message.get('business_connection_id')
        logger.info(f"📊 Business connection ID: {business_connection_id}")
        
        # Обрабатываем как обычное сообщение, но с флагом Business и connection_id
        result = await self._handle_message(
            business_message, 
            is_business=True, 
            business_connection_id=business_connection_id
        )
        
        # Добавляем business_connection_id в метаданные результата
        if result.get('ok'):
            result['business_connection_id'] = business_connection_id
            result['message_type'] = 'business'
        
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
    
    async def _process_voice_transcription(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Транскрибирует голосовое сообщение без MCP"""
        try:
            file_id = voice_data.get('file_id')
            if not file_id:
                return {"success": False, "error": "No file_id in voice data"}
            
            # Используем базовый метод транскрипции
            result = await voice_service.process_voice_message(
                voice_data, 
                str(user_id), 
                str(voice_data.get('file_id', 'unknown'))
            )
            
            return result or {"success": False, "error": "Voice processing failed"}
            
        except Exception as e:
            logger.error(f"❌ Ошибка транскрипции голоса: {e}")
            return {"success": False, "error": f"Ошибка транскрипции: {str(e)}"}
    
    async def _process_voice_to_mcp(self, voice_data: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Обрабатывает голосовое сообщение через MCP (старый метод, оставлен для совместимости)"""
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
            
            elif command == '/business_status':
                # Команда для проверки статуса Business API
                from ..telegram_bot import bot
                logger.info(f"🔍 Business status check requested by {message.user.id}")
                
                try:
                    # Получаем информацию о подключениях
                    connections_info = get_business_connections_info()
                    
                    if connections_info.get("success"):
                        count = connections_info.get("connections_count", 0)
                        status_text = f"📱 **Business API Status**\n\n"
                        status_text += f"Подключений: {count}\n"
                        
                        if count > 0:
                            status_text += "\n**Активные подключения:**\n"
                            for conn in connections_info.get("connections", []):
                                user_info = conn.get("user", {})
                                username = user_info.get("username", "Unknown")
                                is_enabled = conn.get("is_enabled", False)
                                status_emoji = "✅" if is_enabled else "❌"
                                status_text += f"{status_emoji} @{username}\n"
                        else:
                            status_text += "\n⚠️ Нет активных подключений"
                    else:
                        error_details = connections_info.get("details", "Unknown error")
                        status_text = f"❌ **Business API Error**\n\nОшибка: {error_details}"
                    
                    bot.send_message(message.chat_id, status_text, parse_mode='Markdown')
                    logger.info(f"✅ Business status sent to {message.chat_id}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to get business status: {e}", exc_info=True)
                    try:
                        bot.send_message(message.chat_id, f"❌ Ошибка проверки статуса: {str(e)}")
                    except:
                        pass
                
                return {"ok": True, "command": "business_status"}
            
            # MCP команды через унифицированный сервис (только для админов)
            logger.info(f"🔌 Checking MCP commands. Command: {command}, unified_mcp_service: {unified_mcp_service is not None}")
            if unified_mcp_service and unified_mcp_service.is_mcp_command(message.text):
                logger.info(f"🔌 Processing MCP command: {message.text}")
                from ..telegram_bot import bot
                
                try:
                    # Отправляем сообщение о начале обработки
                    bot.send_message(message.chat_id, "⏳ Выполняю MCP команду...")
                    
                    # Выполняем команду через унифицированный сервис
                    response_text = await unified_mcp_service.process_message(message.text)
                    
                    if response_text:
                        # Ограничиваем длину сообщения
                        if len(response_text) > 4000:
                            response_text = response_text[:3997] + "..."
                        
                        # Отправляем результат
                        logger.info(f"📤 Sending MCP response to {message.chat_id}: {response_text[:100]}...")
                        bot.send_message(message.chat_id, response_text, parse_mode='Markdown')
                        logger.info(f"✅ MCP response sent to {message.chat_id}")
                    else:
                        bot.send_message(message.chat_id, "❌ Не удалось выполнить MCP команду")
                    
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
/business_status - Статус Business API
/youtube &lt;url&gt; - Анализ YouTube видео
/status - Статус всех сервисов
/test - Тестовый режим

{agent_section}{mcp_section}<b>📱 Business API:</b>
/business_status - Проверка подключения и статуса

<b>🎤 Голосовые сообщения:</b>
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