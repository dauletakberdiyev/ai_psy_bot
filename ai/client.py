"""OpenAI API client."""
import time
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from openai import AsyncOpenAI

from config import config
from utils.logger import logger
from db.models import LLMRequestRepository


class AIClient:
    """OpenAI API client wrapper."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
        self.model = config.OPENAI_MODEL
        self.max_tokens = config.OPENAI_MAX_TOKENS
        self.temperature = config.OPENAI_TEMPERATURE
        
        logger.info(f"AI Client initialized with model: {self.model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        json_mode: bool = False
    ) -> Tuple[str, Dict]:
        """
        Get chat completion from OpenAI.
        
        Args:
            messages: List of message dicts with role and content
            user_id: User UUID for logging
            session_id: Session UUID for logging
            message_id: Message UUID for logging
            max_tokens: Override default max tokens
            temperature: Override default temperature
            json_mode: Force JSON response format
            
        Returns:
            Tuple of (response_content, usage_stats)
        """
        start_time = time.time()
        
        try:
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature or self.temperature,
            }
            
            # Enable JSON mode if requested
            if json_mode:
                request_params["response_format"] = {"type": "json_object"}
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract response
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate metrics
            latency_ms = int((time.time() - start_time) * 1000)
            cost_usd = self._calculate_cost(usage.prompt_tokens, usage.completion_tokens)
            
            # Log request
            await LLMRequestRepository.create(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                provider="openai",
                model=self.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                status="success"
            )
            
            logger.info(f"AI completion successful - tokens: {usage.total_tokens}, latency: {latency_ms}ms")
            
            return content, {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd
            }
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"AI completion failed: {e}")
            
            # Log error
            await LLMRequestRepository.create(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                provider="openai",
                model=self.model,
                latency_ms=latency_ms,
                status="error",
                error_code=type(e).__name__,
                error_message=str(e)
            )
            
            raise
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate approximate cost for GPT-4o-mini.
        
        Pricing (as of 2024):
        - Input: $0.150 / 1M tokens
        - Output: $0.600 / 1M tokens
        """
        input_cost = (prompt_tokens / 1_000_000) * 0.150
        output_cost = (completion_tokens / 1_000_000) * 0.600
        return round(input_cost + output_cost, 6)


# Global AI client instance
ai_client = AIClient()
