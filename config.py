"""Configuration management for AI Psychologist Bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent


class Config:
    """Application configuration."""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "1500"))
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Database - supports both individual vars and Railway's DATABASE_URL
    DATABASE_URL_ENV = os.getenv("DATABASE_URL", "")  # Railway provides this
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "ai_psycholog")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    @property
    def DATABASE_URL(self) -> str:
        """Build PostgreSQL connection URL."""
        # Use Railway's DATABASE_URL if available, otherwise build from components
        if self.DATABASE_URL_ENV:
            return self.DATABASE_URL_ENV
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    # Application Settings
    DAILY_MESSAGE_LIMIT = int(os.getenv("DAILY_MESSAGE_LIMIT", "20"))
    SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
    MEMORY_SUMMARY_EVERY_N_MESSAGES = int(os.getenv("MEMORY_SUMMARY_EVERY_N_MESSAGES", "10"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Prompt files
    SYSTEM_PROMPT_FILE = BASE_DIR / "system_promt.md"
    CRISIS_PROMPT_FILE = BASE_DIR / "crisis_prompt.md"
    DETECTOR_PROMPT_FILE = BASE_DIR / "detector_prompt.md"
    MEMORY_SUMMARY_PROMPT_FILE = BASE_DIR / "memort_summary_prompt.md"
    MEMORY_FACT_EXTRACTOR_FILE = BASE_DIR / "memory_fact_extractor.md"
    MEMORY_INSERT_PROMPT_FILE = BASE_DIR / "memory_insert_prompt.md"
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of missing required fields."""
        missing = []
        
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        
        # Database: require either DATABASE_URL (Railway) or DB_PASSWORD (local)
        if not self.DATABASE_URL_ENV and not self.DB_PASSWORD:
            missing.append("DB_PASSWORD or DATABASE_URL")
        
        # Check prompt files exist
        for attr_name in ["SYSTEM_PROMPT_FILE", "CRISIS_PROMPT_FILE", "DETECTOR_PROMPT_FILE",
                          "MEMORY_SUMMARY_PROMPT_FILE", "MEMORY_FACT_EXTRACTOR_FILE", 
                          "MEMORY_INSERT_PROMPT_FILE"]:
            file_path = getattr(self, attr_name)
            if not file_path.exists():
                missing.append(f"{attr_name} (file not found: {file_path})")
        
        return missing


# Global config instance
config = Config()
