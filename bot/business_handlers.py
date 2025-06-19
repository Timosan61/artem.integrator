"""
Обработчики для Telegram Business API событий
"""

import logging
from telebot import types
from .handlers import bot
from .agent import process_message_with_ai

logger = logging.getLogger(__name__)

async def handle_business_update(update: types.Update):
    """
    Главная функция обработки Business API событий
    """
    try:
        if hasattr(update, 'business_connection'):
            await handle_business_connection(update.business_connection)
        
        elif hasattr(update, 'business_message'):
            await handle_business_message(update.business_message)
            
        elif hasattr(update, 'edited_business_message'):
            await handle_edited_business_message(update.edited_business_message)
            
        elif hasattr(update, 'deleted_business_messages'):
            await handle_deleted_business_messages(update.deleted_business_messages)
            
        else:
            logger.warning(f"Неизвестный тип business update: {type(update)}")
            
    except Exception as e:
        logger.error(f"Ошибка обработки business update: {e}")

async def handle_business_connection(business_connection):
    """
    Обработка подключения/отключения бизнес аккаунта
    """
    logger.info(f"Business connection: {business_connection.id} - {business_connection.is_enabled}")
    
    if business_connection.is_enabled:
        logger.info(f"✅ Бот подключен к business аккаунту: {business_connection.user.first_name}")
    else:
        logger.info(f"❌ Бот отключен от business аккаунта: {business_connection.user.first_name}")

async def handle_business_message(business_message: types.Message):
    """
    Обработка сообщений от business аккаунта
    """
    try:
        logger.info(f"📨 Business сообщение от {business_message.from_user.first_name}: {business_message.text}")
        
        # Проверяем что сообщение не от нашего бота (избегаем зацикливания)
        if business_message.from_user.is_bot:
            logger.debug("Игнорируем сообщение от бота")
            return
            
        # Обрабатываем текстовые сообщения
        if business_message.text:
            response = await process_message_with_ai(
                user_id=business_message.from_user.id,
                message_text=business_message.text,
                username=business_message.from_user.username or business_message.from_user.first_name
            )
            
            # Отправляем ответ через business API
            bot.send_message(
                chat_id=business_message.chat.id,
                text=response,
                business_connection_id=business_message.business_connection_id
            )
            
            logger.info(f"✅ Отправлен ответ через business API")
            
        # Обрабатываем другие типы сообщений
        elif business_message.photo:
            await handle_business_photo(business_message)
        elif business_message.document:
            await handle_business_document(business_message)
        else:
            logger.info("Получен неподдерживаемый тип business сообщения")
            
    except Exception as e:
        logger.error(f"Ошибка обработки business сообщения: {e}")

async def handle_business_photo(business_message: types.Message):
    """
    Обработка фото от business аккаунта
    """
    try:
        logger.info(f"📷 Получено фото в business чате")
        
        response = "📷 Спасибо за фото! Я вижу изображение, но пока не могу его обработать. Опишите, пожалуйста, ваш вопрос текстом."
        
        bot.send_message(
            chat_id=business_message.chat.id,
            text=response,
            business_connection_id=business_message.business_connection_id
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки business фото: {e}")

async def handle_business_document(business_message: types.Message):
    """
    Обработка документов от business аккаунта
    """
    try:
        logger.info(f"📄 Получен документ в business чате")
        
        response = "📄 Спасибо за документ! Я пока не могу обрабатывать файлы, но готов помочь с вопросами в текстовом формате."
        
        bot.send_message(
            chat_id=business_message.chat.id,
            text=response,
            business_connection_id=business_message.business_connection_id
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки business документа: {e}")

async def handle_edited_business_message(edited_message: types.Message):
    """
    Обработка отредактированных business сообщений
    """
    logger.info(f"✏️ Отредактировано business сообщение: {edited_message.text}")
    # Пока просто логируем, можно добавить логику обработки

async def handle_deleted_business_messages(deleted_messages):
    """
    Обработка удаленных business сообщений
    """
    logger.info(f"🗑️ Удалены business сообщения: {len(deleted_messages.message_ids)} шт.")
    # Пока просто логируем, можно добавить логику обработки