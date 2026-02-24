"""Command handlers for Telegram bot."""
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from uuid import UUID

from db.models import (
    UserRepository, UserSettingsRepository, SessionRepository,
    UsageLimitRepository
)
from utils.i18n import t, STRINGS
from utils.logger import logger


# ---------------------------------------------------------------------------
# All button labels across all languages (used in bot.py to register handlers)
# ---------------------------------------------------------------------------
ALL_BTN_NEW_SESSION = [v for v in STRINGS["btn_new_session"].values()]
ALL_BTN_SETTINGS    = [v for v in STRINGS["btn_settings"].values()]
ALL_BTN_STATS       = [v for v in STRINGS["btn_stats"].values()]
ALL_BTN_HELP        = [v for v in STRINGS["btn_help"].values()]


def get_reply_keyboard(lang: str = 'ru') -> ReplyKeyboardMarkup:
    """Persistent keyboard shown above the message input area."""
    keyboard = [
        [KeyboardButton(t(lang, 'btn_new_session'))],
        [KeyboardButton(t(lang, 'btn_settings')), KeyboardButton(t(lang, 'btn_stats'))],
        [KeyboardButton(t(lang, 'btn_help'))],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def _get_lang(user_id_str: str | None) -> str:
    """Load stored language for a user, defaulting to 'ru'."""
    if not user_id_str:
        return 'ru'
    try:
        return await UserSettingsRepository.get_user_language(UUID(user_id_str))
    except Exception:
        return 'ru'


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - register user and create session."""
    user = update.effective_user
    chat_id = update.effective_chat.id

    try:
        db_user = await UserRepository.create_or_update(
            telegram_user_id=user.id,
            telegram_chat_id=chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code or 'ru'
        )

        user_id = db_user['id']

        await UserSettingsRepository.create_default(user_id)
        await UsageLimitRepository.get_or_create(user_id)

        session = await SessionRepository.get_active(user_id)
        if not session:
            session = await SessionRepository.create(user_id)

        context.user_data['user_id'] = str(user_id)
        context.user_data['session_id'] = str(session['id'])

        lang = await UserSettingsRepository.get_user_language(user_id)

        await update.message.reply_text(
            t(lang, 'welcome', name=user.first_name),
            reply_markup=get_reply_keyboard(lang)
        )
        logger.info(f"User {user.id} started the bot")

    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(t('ru', 'start_error'))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    lang = await _get_lang(context.user_data.get('user_id'))
    await update.message.reply_text(t(lang, 'help_text'), parse_mode='Markdown')


async def newsession_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newsession command - archive current session and create new one."""
    lang = await _get_lang(context.user_data.get('user_id'))
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(t(lang, 'please_start'))
            return

        user_id = UUID(user_id_str)

        current_session = await SessionRepository.get_active(user_id)
        if current_session:
            await SessionRepository.archive(current_session['id'])

        new_session = await SessionRepository.create(user_id)
        context.user_data['session_id'] = str(new_session['id'])

        await update.message.reply_text(t(lang, 'newsession_success'))
        logger.info(f"User {user_id} started new session")

    except Exception as e:
        logger.error(f"Error in newsession_command: {e}")
        await update.message.reply_text(t(lang, 'newsession_error'))


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show current settings."""
    lang = await _get_lang(context.user_data.get('user_id'))
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(t(lang, 'please_start'))
            return

        user_id = UUID(user_id_str)
        settings = await UserSettingsRepository.get(user_id)

        if not settings:
            await update.message.reply_text(t(lang, 'settings_not_found'))
            return

        memory_val = t(lang, 'settings_memory_on' if settings['allow_memory'] else 'settings_memory_off')
        sensitive_val = t(lang, 'settings_sensitive_on' if settings['allow_sensitive_topics'] else 'settings_sensitive_off')

        text = (
            t(lang, 'settings_title')
            + t(lang, 'settings_style', style=settings['preferred_style'])
            + t(lang, 'settings_length', length=settings['response_length'])
            + t(lang, 'settings_memory', value=memory_val)
            + t(lang, 'settings_sensitive', value=sensitive_val)
        )

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in settings_command: {e}")
        await update.message.reply_text(t(lang, 'settings_error'))


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show usage statistics."""
    lang = await _get_lang(context.user_data.get('user_id'))
    try:
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            await update.message.reply_text(t(lang, 'please_start'))
            return

        user_id = UUID(user_id_str)
        usage = await UsageLimitRepository.get_or_create(user_id)
        session = await SessionRepository.get_active(user_id)

        text = (
            t(lang, 'stats_title')
            + t(lang, 'stats_today', used=usage['daily_message_used'], limit=usage['daily_message_limit'])
            + t(lang, 'stats_remaining', remaining=usage['daily_message_limit'] - usage['daily_message_used'])
        )

        if session:
            text += t(lang, 'stats_session_started', date=session['started_at'].strftime('%d.%m.%Y %H:%M'))

        await update.message.reply_text(text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text(t(lang, 'stats_error'))
