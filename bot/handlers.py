import asyncio
import logging
from telebot.async_telebot import AsyncTeleBot
from telebot import types

from .agent import agent
from .config import TELEGRAM_BOT_TOKEN


bot = AsyncTeleBot(TELEGRAM_BOT_TOKEN)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@bot.message_handler(commands=['start'])
async def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    logger.info(f"Пользователь {username} ({user_id}) запустил бота")
    
    welcome_text = agent.get_welcome_message()
    
    await bot.send_message(
        message.chat.id, 
        welcome_text,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['help'])
async def help_command(message):
    help_text = """
🔹 /start - Начать работу с ботом
🔹 /help - Показать это сообщение
🔹 /reload - Перезагрузить инструкции (только для администратора)

Просто напишите ваш вопрос, и я постараюсь помочь!
    """
    
    await bot.send_message(
        message.chat.id,
        help_text,
        parse_mode='Markdown'
    )


@bot.message_handler(commands=['reload'])
async def reload_command(message):
    user_id = message.from_user.id
    
    logger.info(f"Пользователь {user_id} запросил перезагрузку инструкций")
    
    try:
        agent.reload_instruction()
        await bot.send_message(
            message.chat.id,
            "✅ Инструкции успешно перезагружены!"
        )
        logger.info("Инструкции перезагружены")
    except Exception as e:
        await bot.send_message(
            message.chat.id,
            "❌ Ошибка при перезагрузке инструкций"
        )
        logger.error(f"Ошибка при перезагрузке: {e}")


@bot.message_handler(content_types=['text'])
async def handle_text_message(message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    user_message = message.text
    
    logger.info(f"Сообщение от {username} ({user_id}): {user_message[:100]}...")
    
    try:
        await bot.send_chat_action(message.chat.id, 'typing')
        
        session_id = f"user_{user_id}"
        
        response = await agent.generate_response(user_message, session_id)
        
        await bot.send_message(
            message.chat.id,
            response,
            parse_mode='Markdown'
        )
        
        logger.info(f"Ответ отправлен пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        await bot.send_message(
            message.chat.id,
            "Извините, произошла ошибка. Попробуйте позже или обратитесь к нашим специалистам.",
            parse_mode='Markdown'
        )


@bot.message_handler(content_types=['photo', 'document', 'voice', 'video', 'audio'])
async def handle_media_message(message):
    user_id = message.from_user.id
    
    logger.info(f"Медиа сообщение от пользователя {user_id}")
    
    await bot.send_message(
        message.chat.id,
        "Спасибо за отправленный файл! В данный момент я работаю только с текстовыми сообщениями. "
        "Опишите ваш вопрос текстом, и я с радостью помогу! 📝"
    )


async def run_bot():
    logger.info("Запуск бота...")
    await bot.infinity_polling()