"""Command handlers for Telegram bot."""
from telegram import Update
from telegram.ext import ContextTypes
from uuid import UUID

from db.models import (
    UserRepository, UserSettingsRepository, SessionRepository,
    UsageLimitRepository
)
from utils.logger import logger


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - register user and create session."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    try:
        # Create or update user
        db_user = await UserRepository.create_or_update(
            telegram_user_id=user.id,
            telegram_chat_id=chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or 'ru'
        )
        
        user_id = db_user['id']
        
        # Create default settings
        await UserSettingsRepository.create_default(user_id)
        
        # Create usage limit record
        await UsageLimitRepository.get_or_create(user_id)
        
        # Create active session
        session = await SessionRepository.get_active(user_id)
        if not session:
            session = await SessionRepository.create(user_id)
        
        # Store user_id in context for future use
        context.user_data['user_id'] = str(user_id)
        context.user_data['session_id'] = str(session['id'])
        
        # Welcome message
        welcome_text = (
            f"Привет, {user.first_name}! 👋\n\n"
            "Я AI-психолог поддержки, работающий в подходе CBT (когнитивно-поведенческая терапия).\n\n"
            "Я помогу тебе:\n"
            "• Снизить тревогу и стресс\n"
            "• Лучше понять свои эмоции и мысли\n"
            "• Научиться замечать когнитивные искажения\n"
            "• Выбирать более полезные действия\n\n"
            "⚠️ Важно: я не врач и не психотерапевт. Я не ставлю диагнозы и не заменяю очную терапию.\n\n"
            "Просто напиши мне, что тебя беспокоит, и я постараюсь помочь.\n\n"
            "Команды:\n"
            "/newsession - начать новую сессию\n"
            "/settings - настройки\n"
            "/stats - статистика использования\n"
            "/help - помощь"
        )
        
        await update.message.reply_text(welcome_text)
        logger.info(f"User {user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(
            "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "📖 *Как пользоваться ботом*\n\n"
        "Просто напиши мне, что тебя беспокоит, и я помогу разобраться.\n\n"
        "*Команды:*\n"
        "/start - начать работу с ботом\n"
        "/newsession - архивировать текущую сессию и начать новую\n"
        "/settings - изменить настройки (стиль общения, длина ответов)\n"
        "/stats - посмотреть статистику использования\n"
        "/help - показать это сообщение\n\n"
        "*Лимиты:*\n"
        "Бесплатно: 20 сообщений в день\n\n"
        "*Важно помнить:*\n"
        "• Я не врач и не психотерапевт\n"
        "• Я не ставлю диагнозы\n"
        "• В экстренной ситуации обратитесь к специалистам\n\n"
        "Если у тебя есть вопросы, просто спроси!"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newsession command - archive current session and create new one."""
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(
                "Сначала используй /start для регистрации."
            )
            return
        
        user_id = UUID(user_id_str)
        
        # Archive current session
        current_session = await SessionRepository.get_active(user_id)
        if current_session:
            await SessionRepository.archive(current_session['id'])
        
        # Create new session
        new_session = await SessionRepository.create(user_id)
        context.user_data['session_id'] = str(new_session['id'])
        
        await update.message.reply_text(
            "✅ Новая сессия начата!\n\n"
            "Предыдущая сессия архивирована. "
            "Расскажи, что тебя беспокоит сейчас?"
        )
        logger.info(f"User {user_id} started new session")
        
    except Exception as e:
        logger.error(f"Error in newsession_command: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже."
        )


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show current settings."""
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(
                "Сначала используй /start для регистрации."
            )
            return
        
        user_id = UUID(user_id_str)
        settings = await UserSettingsRepository.get(user_id)
        
        if not settings:
            await update.message.reply_text("Настройки не найдены.")
            return
        
        settings_text = (
            "⚙️ *Текущие настройки:*\n\n"
            f"Стиль общения: `{settings['preferred_style']}`\n"
            f"Длина ответов: `{settings['response_length']}`\n"
            f"Память: `{'включена' if settings['allow_memory'] else 'выключена'}`\n"
            f"Чувствительные темы: `{'разрешены' if settings['allow_sensitive_topics'] else 'запрещены'}`\n\n"
            "Для изменения настроек напишите мне, и я помогу."
        )
        
        await update.message.reply_text(settings_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in settings_command: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке настроек.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show usage statistics."""
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(
                "Сначала используй /start для регистрации."
            )
            return
        
        user_id = UUID(user_id_str)
        
        # Get usage limits
        usage = await UsageLimitRepository.get_or_create(user_id)
        
        # Get session info
        session = await SessionRepository.get_active(user_id)
        
        stats_text = (
            "📊 *Статистика использования:*\n\n"
            f"Сообщений сегодня: {usage['daily_message_used']}/{usage['daily_message_limit']}\n"
            f"Осталось: {usage['daily_message_limit'] - usage['daily_message_used']}\n\n"
        )
        
        if session:
            stats_text += f"Текущая сессия начата: {session['started_at'].strftime('%d.%m.%Y %H:%M')}\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text("Произошла ошибка при загрузке статистики.")
