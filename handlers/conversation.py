"""Conversation handler for user messages."""
from telegram import Update
from telegram.ext import ContextTypes
from uuid import UUID

from db.models import (
    UserRepository, UserSettingsRepository, SessionRepository,
    MessageRepository, UsageLimitRepository
)
from ai.client import ai_client
from ai.prompts import prompt_manager
from ai.detector import risk_detector
from ai.memory import memory_manager
from config import config
from utils.i18n import t
from utils.logger import logger

# Language names for the system prompt instruction
_LANG_NAMES = {
    'ru': 'Russian',
    'kz': 'Kazakh',
    'en': 'English',
}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text messages."""
    user = update.effective_user
    user_message = update.message.text

    try:
        # Get or create user
        user_id_str = context.user_data.get('user_id')
        if not user_id_str:
            # Auto-register user
            db_user = await UserRepository.get_by_telegram_id(user.id)
            if not db_user:
                await update.message.reply_text(t('ru', 'use_start_first'))
                return
            user_id = db_user['id']
            context.user_data['user_id'] = str(user_id)
        else:
            user_id = UUID(user_id_str)

        # Load user language early so all error messages are correctly localised
        lang = await UserSettingsRepository.get_user_language(user_id)

        # Check usage limits
        can_send = await UsageLimitRepository.check_limit(user_id)
        if not can_send:
            await update.message.reply_text(t(lang, 'limit_reached'))
            return

        # Get or create active session
        session = await SessionRepository.get_active(user_id)
        if not session:
            session = await SessionRepository.create(user_id)
            context.user_data['session_id'] = str(session['id'])

        session_id = session['id']

        # Save user message
        user_msg_record = await MessageRepository.create(
            session_id=session_id,
            user_id=user_id,
            role='user',
            content=user_message
        )

        # Update session timestamp
        await SessionRepository.update_last_message_time(session_id)

        # Detect risk
        need_crisis_mode, risk_result = await risk_detector.analyze(
            user_message=user_message,
            user_id=user_id,
            session_id=session_id,
            message_id=user_msg_record['id']
        )

        # Get user settings
        settings = await UserSettingsRepository.get(user_id)
        if not settings:
            settings = await UserSettingsRepository.create_default(user_id)

        # Get memory context (if allowed and not in crisis mode)
        memory_summary = None
        memory_facts = None
        if not need_crisis_mode and settings['allow_memory']:
            memory_summary, memory_facts = await memory_manager.get_memory_context(user_id)

        # Build system prompt
        system_prompt = prompt_manager.build_system_prompt(
            crisis_mode=need_crisis_mode,
            user_settings=settings,
            memory_summary=memory_summary,
            memory_facts=memory_facts
        )

        # Append language instruction so GPT always replies in the user's chosen language
        lang_name = _LANG_NAMES.get(lang, 'Russian')
        system_prompt += f"\n\nIMPORTANT: Always reply in {lang_name}, regardless of the language the user writes in."

        # Get recent conversation history
        recent_messages = await MessageRepository.get_session_messages(session_id, limit=20)
        conversation_history = []
        for msg in recent_messages[:-1]:  # Exclude the message we just saved
            if msg['role'] in ['user', 'assistant']:
                conversation_history.append({
                    'role': msg['role'],
                    'content': msg['content']
                })

        # Add current user message
        conversation_history.append({
            'role': 'user',
            'content': user_message
        })

        # Format messages for API
        api_messages = prompt_manager.format_messages_for_openai(
            system_prompt=system_prompt,
            conversation_history=conversation_history
        )

        # Show typing indicator
        await update.message.chat.send_action("typing")

        # Get AI response
        ai_response, stats = await ai_client.chat_completion(
            messages=api_messages,
            user_id=user_id,
            session_id=session_id,
            message_id=user_msg_record['id']
        )

        # Save assistant message
        await MessageRepository.create(
            session_id=session_id,
            user_id=user_id,
            role='assistant',
            content=ai_response,
            meta={'crisis_mode': need_crisis_mode, 'risk': risk_result['risk']}
        )

        # Send response to user
        await update.message.reply_text(ai_response)

        # Increment usage counter
        await UsageLimitRepository.increment_usage(user_id)

        # Create memory summary periodically
        message_count = await MessageRepository.count_session_messages(session_id)
        if message_count % config.MEMORY_SUMMARY_EVERY_N_MESSAGES == 0:
            try:
                await memory_manager.create_session_summary(user_id, session_id)
                await memory_manager.extract_and_update_facts(user_id, session_id)
                logger.info(f"Memory updated for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to update memory: {e}")

        logger.info(
            f"Message handled - user: {user.id}, "
            f"lang: {lang}, "
            f"crisis: {need_crisis_mode}, "
            f"tokens: {stats.get('total_tokens', 0)}"
        )

    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        try:
            lang = await UserSettingsRepository.get_user_language(UUID(context.user_data.get('user_id', '')))
        except Exception:
            lang = 'ru'
        await update.message.reply_text(t(lang, 'conversation_error'))


async def handle_error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)

    if update and update.effective_message:
        await update.effective_message.reply_text(t('ru', 'unexpected_error'))
