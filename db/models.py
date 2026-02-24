"""Database models and repository pattern for all tables."""
from typing import Optional, Dict, Any, List
from datetime import datetime, date
import json
from uuid import UUID

from db.database import db
from utils.logger import logger


class UserRepository:
    """Repository for users table."""
    
    @staticmethod
    async def create_or_update(
        telegram_user_id: int,
        telegram_chat_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: str = "ru"
    ) -> Dict[str, Any]:
        """Create new user or update existing one."""
        query = """
            INSERT INTO users (telegram_user_id, telegram_chat_id, username, first_name, last_name, language_code)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (telegram_user_id) 
            DO UPDATE SET 
                telegram_chat_id = EXCLUDED.telegram_chat_id,
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                updated_at = now()
            RETURNING *
        """
        row = await db.fetchrow(query, telegram_user_id, telegram_chat_id, username, 
                                first_name, last_name, language_code)
        return dict(row)
    
    @staticmethod
    async def get_by_telegram_id(telegram_user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Telegram user ID."""
        query = "SELECT * FROM users WHERE telegram_user_id = $1"
        row = await db.fetchrow(query, telegram_user_id)
        return dict(row) if row else None
    
    @staticmethod
    async def get_by_id(user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user by UUID."""
        query = "SELECT * FROM users WHERE id = $1"
        row = await db.fetchrow(query, user_id)
        return dict(row) if row else None


class UserSettingsRepository:
    """Repository for user_settings table."""
    
    @staticmethod
    async def create_default(user_id: UUID) -> Dict[str, Any]:
        """Create default settings for user."""
        query = """
            INSERT INTO user_settings (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING *
        """
        row = await db.fetchrow(query, user_id)
        return dict(row) if row else await UserSettingsRepository.get(user_id)
    
    @staticmethod
    async def get(user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get user settings."""
        query = "SELECT * FROM user_settings WHERE user_id = $1"
        row = await db.fetchrow(query, user_id)
        return dict(row) if row else None
    
    @staticmethod
    async def update(user_id: UUID, **kwargs) -> Dict[str, Any]:
        """Update user settings."""
        valid_fields = ['preferred_style', 'response_length', 'allow_memory', 'allow_sensitive_topics', 'language']
        updates = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not updates:
            return await UserSettingsRepository.get(user_id)
        
        set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
        query = f"UPDATE user_settings SET {set_clause}, updated_at = now() WHERE user_id = $1 RETURNING *"
        
        row = await db.fetchrow(query, user_id, *updates.values())
        return dict(row)
    
    @staticmethod
    async def get_user_language(user_id: UUID) -> str:
        """Return the user's chosen language code, defaulting to 'ru'."""
        settings = await UserSettingsRepository.get(user_id)
        if settings:
            return settings.get('language', 'ru') or 'ru'
        return 'ru'

    @staticmethod
    async def set_user_language(user_id: UUID, lang: str) -> None:
        """Persist the user's chosen language code."""
        await UserSettingsRepository.update(user_id, language=lang)


class SessionRepository:
    """Repository for sessions table."""
    
    @staticmethod
    async def create(user_id: UUID) -> Dict[str, Any]:
        """Create new session."""
        query = """
            INSERT INTO sessions (user_id, status)
            VALUES ($1, 'active')
            RETURNING *
        """
        row = await db.fetchrow(query, user_id)
        return dict(row)
    
    @staticmethod
    async def get_active(user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get active session for user."""
        query = """
            SELECT * FROM sessions 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
        """
        row = await db.fetchrow(query, user_id)
        return dict(row) if row else None
    
    @staticmethod
    async def archive(session_id: UUID) -> None:
        """Archive a session."""
        query = """
            UPDATE sessions 
            SET status = 'archived', ended_at = now()
            WHERE id = $1
        """
        await db.execute(query, session_id)
    
    @staticmethod
    async def update_last_message_time(session_id: UUID) -> None:
        """Update last message timestamp."""
        query = "UPDATE sessions SET last_message_at = now() WHERE id = $1"
        await db.execute(query, session_id)


class MessageRepository:
    """Repository for messages table."""
    
    @staticmethod
    async def create(
        session_id: UUID,
        user_id: UUID,
        role: str,
        content: str,
        meta: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create new message."""
        query = """
            INSERT INTO messages (session_id, user_id, role, content, meta)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """
        meta_json = json.dumps(meta or {})
        row = await db.fetchrow(query, session_id, user_id, role, content, meta_json)
        return dict(row)
    
    @staticmethod
    async def get_session_messages(session_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages for a session."""
        query = """
            SELECT * FROM messages 
            WHERE session_id = $1
            ORDER BY created_at ASC
            LIMIT $2
        """
        rows = await db.fetch(query, session_id, limit)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def count_session_messages(session_id: UUID) -> int:
        """Count messages in a session."""
        query = "SELECT COUNT(*) FROM messages WHERE session_id = $1"
        return await db.fetchval(query, session_id)


class RiskEventRepository:
    """Repository for risk_events table."""
    
    @staticmethod
    async def create(
        user_id: UUID,
        session_id: Optional[UUID],
        message_id: Optional[UUID],
        risk: str,
        category: str,
        reasons: List[str],
        raw_detector_output: Dict
    ) -> Dict[str, Any]:
        """Create new risk event."""
        query = """
            INSERT INTO risk_events 
            (user_id, session_id, message_id, risk, category, reasons, raw_detector_output)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        raw_json = json.dumps(raw_detector_output)
        row = await db.fetchrow(query, user_id, session_id, message_id, 
                               risk, category, reasons, raw_json)
        return dict(row)
    
    @staticmethod
    async def get_recent_high_risk(user_id: UUID, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent high-risk events for user."""
        query = """
            SELECT * FROM risk_events 
            WHERE user_id = $1 AND risk IN ('medium', 'high')
            ORDER BY created_at DESC
            LIMIT $2
        """
        rows = await db.fetch(query, user_id, limit)
        return [dict(row) for row in rows]


class MemoryRepository:
    """Repository for memory_summaries and memory_facts tables."""
    
    @staticmethod
    async def create_summary(
        user_id: UUID,
        session_id: UUID,
        summary: str,
        main_topics: List[str],
        user_emotions: List[str],
        key_thoughts: List[str],
        triggers: List[str],
        helpful_strategies_used: List[str],
        next_session_goal: str
    ) -> Dict[str, Any]:
        """Create memory summary."""
        query = """
            INSERT INTO memory_summaries 
            (user_id, session_id, summary, main_topics, user_emotions, key_thoughts, 
             triggers, helpful_strategies_used, next_session_goal)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """
        row = await db.fetchrow(query, user_id, session_id, summary, main_topics,
                               user_emotions, key_thoughts, triggers, 
                               helpful_strategies_used, next_session_goal)
        return dict(row)
    
    @staticmethod
    async def get_recent_summaries(user_id: UUID, limit: int = 3) -> List[Dict[str, Any]]:
        """Get recent memory summaries for user."""
        query = """
            SELECT * FROM memory_summaries 
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        rows = await db.fetch(query, user_id, limit)
        return [dict(row) for row in rows]
    
    @staticmethod
    async def upsert_facts(user_id: UUID, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update memory facts."""
        query = """
            INSERT INTO memory_facts 
            (user_id, profile, stable_issues, values_and_goals, common_triggers, 
             cognitive_patterns, preferred_support_style, hard_limits)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (user_id) 
            DO UPDATE SET
                profile = EXCLUDED.profile,
                stable_issues = EXCLUDED.stable_issues,
                values_and_goals = EXCLUDED.values_and_goals,
                common_triggers = EXCLUDED.common_triggers,
                cognitive_patterns = EXCLUDED.cognitive_patterns,
                preferred_support_style = EXCLUDED.preferred_support_style,
                hard_limits = EXCLUDED.hard_limits,
                updated_at = now()
            RETURNING *
        """
        profile_json = json.dumps(facts.get('profile', {}))
        row = await db.fetchrow(
            query, user_id, profile_json,
            facts.get('stable_issues', []),
            facts.get('values_and_goals', []),
            facts.get('common_triggers', []),
            facts.get('cognitive_patterns', []),
            facts.get('preferred_support_style', []),
            facts.get('hard_limits', [])
        )
        return dict(row)
    
    @staticmethod
    async def get_facts(user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get memory facts for user."""
        query = "SELECT * FROM memory_facts WHERE user_id = $1"
        row = await db.fetchrow(query, user_id)
        return dict(row) if row else None


class UsageLimitRepository:
    """Repository for usage_limits table."""
    
    @staticmethod
    async def get_or_create(user_id: UUID, daily_limit: int = 20) -> Dict[str, Any]:
        """Get or create usage limit record."""
        query = """
            INSERT INTO usage_limits (user_id, daily_message_limit)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO NOTHING
            RETURNING *
        """
        await db.execute(query, user_id, daily_limit)
        
        # Get the record (whether newly created or existing)
        query = "SELECT * FROM usage_limits WHERE user_id = $1"
        row = await db.fetchrow(query, user_id)
        return dict(row)
    
    @staticmethod
    async def increment_usage(user_id: UUID) -> Dict[str, Any]:
        """Increment daily message count, reset if new day."""
        query = """
            UPDATE usage_limits
            SET 
                daily_message_used = CASE 
                    WHEN daily_reset_at < CURRENT_DATE THEN 1
                    ELSE daily_message_used + 1
                END,
                daily_reset_at = CURRENT_DATE,
                updated_at = now()
            WHERE user_id = $1
            RETURNING *
        """
        row = await db.fetchrow(query, user_id)
        return dict(row)
    
    @staticmethod
    async def check_limit(user_id: UUID) -> bool:
        """Check if user has exceeded daily limit."""
        limits = await UsageLimitRepository.get_or_create(user_id)
        
        # Reset if new day
        if limits['daily_reset_at'] < date.today():
            limits = await UsageLimitRepository.increment_usage(user_id)
            return True
        
        return limits['daily_message_used'] < limits['daily_message_limit']


class LLMRequestRepository:
    """Repository for llm_requests table."""
    
    @staticmethod
    async def create(
        user_id: Optional[UUID],
        session_id: Optional[UUID],
        message_id: Optional[UUID],
        provider: str,
        model: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
        cost_usd: Optional[float] = None,
        status: str = "success",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log LLM request."""
        query = """
            INSERT INTO llm_requests 
            (user_id, session_id, message_id, provider, model, prompt_tokens, 
             completion_tokens, total_tokens, latency_ms, cost_usd, status, 
             error_code, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING *
        """
        row = await db.fetchrow(
            query, user_id, session_id, message_id, provider, model,
            prompt_tokens, completion_tokens, total_tokens, latency_ms,
            cost_usd, status, error_code, error_message
        )
        return dict(row)
