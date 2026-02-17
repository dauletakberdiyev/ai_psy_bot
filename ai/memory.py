"""Memory management system."""
import json
from typing import Dict, List, Optional
from uuid import UUID

from ai.client import ai_client
from ai.prompts import prompt_manager
from db.models import MemoryRepository, MessageRepository
from utils.logger import logger


class MemoryManager:
    """Manages session summaries and long-term memory facts."""
    
    async def create_session_summary(
        self,
        user_id: UUID,
        session_id: UUID
    ) -> Optional[Dict]:
        """
        Create summary of a session.
        
        Args:
            user_id: User UUID
            session_id: Session UUID
            
        Returns:
            Summary dict or None if failed
        """
        try:
            # Get session messages
            messages = await MessageRepository.get_session_messages(session_id, limit=100)
            
            if len(messages) < 3:
                logger.info("Not enough messages for summary")
                return None
            
            # Build conversation text
            conversation = self._format_conversation_for_summary(messages)
            
            # Get AI summary
            prompt_messages = [
                {"role": "system", "content": prompt_manager.memory_summary_prompt},
                {"role": "user", "content": conversation}
            ]
            
            response, _ = await ai_client.chat_completion(
                messages=prompt_messages,
                user_id=user_id,
                session_id=session_id,
                temperature=0.5,
                json_mode=True
            )
            
            # Parse response
            summary_data = json.loads(response)
            
            # Save to database
            await MemoryRepository.create_summary(
                user_id=user_id,
                session_id=session_id,
                summary=summary_data.get('summary', ''),
                main_topics=summary_data.get('main_topics', []),
                user_emotions=summary_data.get('user_emotions', []),
                key_thoughts=summary_data.get('key_thoughts', []),
                triggers=summary_data.get('triggers', []),
                helpful_strategies_used=summary_data.get('helpful_strategies_used', []),
                next_session_goal=summary_data.get('next_session_goal', '')
            )
            
            logger.info(f"Session summary created for session {session_id}")
            return summary_data
            
        except Exception as e:
            logger.error(f"Failed to create session summary: {e}")
            return None
    
    async def extract_and_update_facts(
        self,
        user_id: UUID,
        session_id: UUID
    ) -> Optional[Dict]:
        """
        Extract long-term facts from session and update user's memory facts.
        
        Args:
            user_id: User UUID
            session_id: Session UUID
            
        Returns:
            Updated facts dict or None if failed
        """
        try:
            # Get session messages
            messages = await MessageRepository.get_session_messages(session_id, limit=100)
            
            if len(messages) < 5:
                logger.info("Not enough messages for fact extraction")
                return None
            
            # Build conversation text
            conversation = self._format_conversation_for_summary(messages)
            
            # Get existing facts
            existing_facts = await MemoryRepository.get_facts(user_id)
            
            # Build prompt with existing facts
            prompt_text = "ПРЕДЫДУЩИЕ ФАКТЫ:\n"
            if existing_facts:
                prompt_text += json.dumps({
                    'profile': existing_facts.get('profile', {}),
                    'stable_issues': existing_facts.get('stable_issues', []),
                    'values_and_goals': existing_facts.get('values_and_goals', []),
                    'common_triggers': existing_facts.get('common_triggers', []),
                    'cognitive_patterns': existing_facts.get('cognitive_patterns', []),
                    'preferred_support_style': existing_facts.get('preferred_support_style', []),
                    'hard_limits': existing_facts.get('hard_limits', [])
                }, ensure_ascii=False, indent=2)
            else:
                prompt_text += "Нет данных.\n"
            
            prompt_text += f"\n\nНОВЫЙ ДИАЛОГ:\n{conversation}\n\n"
            prompt_text += "Обнови факты на основе нового диалога. Сохрани старые факты, добавь новые."
            
            # Get AI extraction
            prompt_messages = [
                {"role": "system", "content": prompt_manager.memory_fact_extractor_prompt},
                {"role": "user", "content": prompt_text}
            ]
            
            response, _ = await ai_client.chat_completion(
                messages=prompt_messages,
                user_id=user_id,
                session_id=session_id,
                temperature=0.5,
                json_mode=True
            )
            
            # Parse response
            new_facts = json.loads(response)
            
            # Merge with existing facts
            merged_facts = self._merge_facts(existing_facts, new_facts)
            
            # Save to database
            await MemoryRepository.upsert_facts(user_id, merged_facts)
            
            logger.info(f"Memory facts updated for user {user_id}")
            return merged_facts
            
        except Exception as e:
            logger.error(f"Failed to extract memory facts: {e}")
            return None
    
    async def get_memory_context(self, user_id: UUID) -> tuple[Optional[str], Optional[Dict]]:
        """
        Get memory context for conversation.
        
        Args:
            user_id: User UUID
            
        Returns:
            Tuple of (summary_text, facts_dict)
        """
        # Get recent summaries
        summaries = await MemoryRepository.get_recent_summaries(user_id, limit=2)
        summary_text = None
        if summaries:
            # Combine recent summaries
            summary_parts = []
            for s in summaries:
                summary_parts.append(s['summary'])
            summary_text = "\n\n".join(summary_parts)
        
        # Get facts
        facts = await MemoryRepository.get_facts(user_id)
        facts_dict = None
        if facts:
            facts_dict = {
                'profile': facts.get('profile', {}),
                'stable_issues': facts.get('stable_issues', []),
                'values_and_goals': facts.get('values_and_goals', []),
                'common_triggers': facts.get('common_triggers', []),
                'cognitive_patterns': facts.get('cognitive_patterns', []),
                'preferred_support_style': facts.get('preferred_support_style', []),
                'hard_limits': facts.get('hard_limits', [])
            }
        
        return summary_text, facts_dict
    
    @staticmethod
    def _format_conversation_for_summary(messages: List[Dict]) -> str:
        """Format messages for summarization."""
        lines = []
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == 'user':
                lines.append(f"Пользователь: {content}")
            elif role == 'assistant':
                lines.append(f"Психолог: {content}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _merge_facts(existing: Optional[Dict], new: Dict) -> Dict:
        """Merge existing facts with new facts."""
        if not existing:
            return new
        
        merged = {}
        
        # Merge profile
        merged['profile'] = {**existing.get('profile', {}), **new.get('profile', {})}
        
        # Merge arrays (deduplicate)
        for key in ['stable_issues', 'values_and_goals', 'common_triggers', 
                    'cognitive_patterns', 'preferred_support_style', 'hard_limits']:
            existing_items = set(existing.get(key, []))
            new_items = set(new.get(key, []))
            merged[key] = list(existing_items | new_items)
        
        return merged


# Global memory manager instance
memory_manager = MemoryManager()
