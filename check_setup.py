"""Quick setup script to help verify configuration."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config


def main():
    """Verify configuration and setup."""
    print("=" * 60)
    print("AI Psychologist Bot - Configuration Check")
    print("=" * 60)
    print()
    
    # Check configuration
    missing = config.validate()
    
    if missing:
        print("❌ Configuration Incomplete!\n")
        print("Missing required settings:")
        for item in missing:
            print(f"  - {item}")
        print("\n📝 Next Steps:")
        print("1. Copy .env.example to .env")
        print("2. Edit .env and fill in the required values")
        print("3. Run this script again")
        return 1
    
    print("✅ Configuration Valid!\n")
    print("Settings:")
    print(f"  • Telegram Bot Token: {'*' * 10}{config.TELEGRAM_BOT_TOKEN[-5:]}")
    print(f"  • OpenAI API Key: {'*' * 10}{config.OPENAI_API_KEY[-5:]}")
    print(f"  • OpenAI Model: {config.OPENAI_MODEL}")
    print(f"  • Database: {config.DB_NAME}@{config.DB_HOST}:{config.DB_PORT}")
    print(f"  • Daily Message Limit: {config.DAILY_MESSAGE_LIMIT}")
    print()
    
    # Check prompt files
    print("Prompt Files:")
    all_prompts_ok = True
    for attr in ['SYSTEM_PROMPT_FILE', 'CRISIS_PROMPT_FILE', 'DETECTOR_PROMPT_FILE',
                 'MEMORY_SUMMARY_PROMPT_FILE', 'MEMORY_FACT_EXTRACTOR_FILE', 
                 'MEMORY_INSERT_PROMPT_FILE']:
        file_path = getattr(config, attr)
        exists = file_path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {file_path.name}")
        if not exists:
            all_prompts_ok = False
    
    print()
    
    if not all_prompts_ok:
        print("❌ Some prompt files are missing!")
        return 1
    
    print("=" * 60)
    print("🚀 Ready to run!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set up PostgreSQL database:")
    print("   createdb ai_psycholog")
    print("   psql -d ai_psycholog -f db/database_creation.sql")
    print()
    print("2. Start the bot:")
    print("   python bot.py")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
