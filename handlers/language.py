"""Language selection handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from uuid import UUID

from db.models import UserRepository, UserSettingsRepository
from handlers.commands import get_reply_keyboard
from utils.i18n import t, SUPPORTED_LANGUAGES
from utils.logger import logger


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /language command — show language selection keyboard."""
    user = update.effective_user

    # Determine current language for the prompt text
    user_id_str = context.user_data.get('user_id')
    lang = 'ru'
    if user_id_str:
        try:
            lang = await UserSettingsRepository.get_user_language(UUID(user_id_str))
        except Exception:
            pass

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский",  callback_data="lang:ru")],
        [InlineKeyboardButton("🇰🇿 Қазақша", callback_data="lang:kz")],
        [InlineKeyboardButton("🇬🇧 English",  callback_data="lang:en")],
    ])

    await update.message.reply_text(t(lang, 'language_prompt'), reply_markup=keyboard)


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button tap — save chosen language and confirm."""
    query = update.callback_query
    await query.answer()

    chosen_lang = query.data.split(":")[1]  # e.g. "lang:en" → "en"
    if chosen_lang not in SUPPORTED_LANGUAGES:
        chosen_lang = 'ru'

    user = update.effective_user

    try:
        # Resolve user_id
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            db_user = await UserRepository.get_by_telegram_id(user.id)
            if not db_user:
                await query.edit_message_text(t('ru', 'use_start_first'))
                return
            user_id = db_user['id']
            context.user_data['user_id'] = str(user_id)
        else:
            user_id = UUID(user_id_str)

        # Ensure settings row exists
        await UserSettingsRepository.create_default(user_id)

        # Persist the language choice
        await UserSettingsRepository.set_user_language(user_id, chosen_lang)

        # Update the inline message with confirmation
        await query.edit_message_text(t(chosen_lang, 'language_set'))

        # Send the updated reply keyboard in the new language
        await update.effective_chat.send_message(
            text="✓",
            reply_markup=get_reply_keyboard(chosen_lang),
        )

        logger.info(f"User {user.id} changed language to '{chosen_lang}'")

    except Exception as e:
        logger.error(f"Error in handle_language_callback: {e}")
        await query.edit_message_text(t('ru', 'language_error'))
