"""Prompt management system."""
from pathlib import Path
from typing import Dict, List, Optional
import json

from config import config
from utils.logger import logger


class PromptManager:
    """Manages loading and formatting of prompt templates."""
    
    def __init__(self):
        self.system_prompt = self._load_file(config.SYSTEM_PROMPT_FILE)
        self.crisis_prompt = self._load_file(config.CRISIS_PROMPT_FILE)
        self.detector_prompt = self._load_file(config.DETECTOR_PROMPT_FILE)
        self.memory_summary_prompt = self._load_file(config.MEMORY_SUMMARY_PROMPT_FILE)
        self.memory_fact_extractor_prompt = self._load_file(config.MEMORY_FACT_EXTRACTOR_FILE)
        self.memory_insert_template = self._load_file(config.MEMORY_INSERT_PROMPT_FILE)
        
        logger.info("Prompts loaded successfully")
    
    @staticmethod
    def _load_file(file_path: Path) -> str:
        """Load prompt file content."""
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Failed to load prompt file {file_path}: {e}")
            raise
    
    def build_system_prompt(
        self, 
        crisis_mode: bool = False,
        user_settings: Optional[Dict] = None,
        memory_summary: Optional[str] = None,
        memory_facts: Optional[Dict] = None
    ) -> str:
        """
        Build system prompt with optional memory context.
        
        Args:
            crisis_mode: Use crisis prompt instead of normal prompt
            user_settings: User preferences (style, response length)
            memory_summary: Recent session summaries
            memory_facts: Long-term user facts
            
        Returns:
            Complete system prompt
        """
        # Choose base prompt
        base_prompt = self.crisis_prompt if crisis_mode else self.system_prompt
        
        # Add user preferences if provided
        if user_settings and not crisis_mode:
            style = user_settings.get('preferred_style', 'cbt')
            length = user_settings.get('response_length', 'medium')
            
            preferences = f"\n\nПредпочтения пользователя:\n"
            preferences += f"- Стиль: {style}\n"
            preferences += f"- Длина ответа: {length}\n"
            
            base_prompt += preferences
        
        # Inject memory context if allowed and provided
        if not crisis_mode and user_settings and user_settings.get('allow_memory', True):
            memory_context = self._build_memory_context(memory_summary, memory_facts)
            if memory_context:
                base_prompt += "\n\n" + memory_context
        
        return base_prompt
    
    def _build_memory_context(
        self, 
        summary: Optional[str], 
        facts: Optional[Dict]
    ) -> str:
        """Build memory context section."""
        if not summary and not facts:
            return ""
        
        context = self.memory_insert_template
        
        # Replace summary placeholder
        summary_text = summary if summary else "Нет предыдущих сессий."
        context = context.replace("{{summary}}", summary_text)
        
        # Replace facts placeholder
        facts_text = json.dumps(facts, ensure_ascii=False, indent=2) if facts else "{}"
        context = context.replace("{{facts_json}}", facts_text)
        
        return context
    
    def format_messages_for_openai(
        self, 
        system_prompt: str, 
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Format messages for OpenAI API.
        
        Args:
            system_prompt: System prompt
            conversation_history: List of {"role": "user"|"assistant", "content": "..."}
            
        Returns:
            Formatted messages list
        """
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        return messages


# Global prompt manager instance
prompt_manager = PromptManager()
