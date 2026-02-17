"""Main Telegram bot application."""
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters
)

from config import config
from db.database import db
from handlers.commands import (
    start_command,
    help_command,
    newsession_command,
    settings_command,
    stats_command
)
from handlers.conversation import handle_message, handle_error
from utils.logger import logger


async def post_init(application: Application):
    """Run after bot initialization."""
    # Connect to database in the bot's event loop
    await db.connect()
    logger.info("Bot initialized successfully")


async def post_shutdown(application: Application):
    """Run after bot shutdown."""
    await db.disconnect()
    logger.info("Bot shut down successfully")


def main():
    """Main entry point for the bot."""
    # Validate configuration
    missing_config = config.validate()
    if missing_config:
        logger.error(f"Missing required configuration: {', '.join(missing_config)}")
        print("\n❌ Configuration Error!")
        print("Missing required environment variables:")
        for item in missing_config:
            print(f"  - {item}")
        print("\nPlease create a .env file based on .env.example and fill in the required values.")
        return
    
    logger.info("Starting AI Psychologist Telegram Bot...")
    logger.info(f"Using model: {config.OPENAI_MODEL}")
    
    # Create application
    application = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("newsession", newsession_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add message handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    
    # Add error handler
    application.add_error_handler(handle_error)
    
    # Run bot
    logger.info("Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
