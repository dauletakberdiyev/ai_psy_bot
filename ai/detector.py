"""Risk detection system."""
import json
from typing import Dict, Tuple
from uuid import UUID

from ai.client import ai_client
from ai.prompts import prompt_manager
from db.models import RiskEventRepository
from utils.logger import logger


class RiskDetector:
    """Detects crisis situations in user messages."""
    
    async def analyze(
        self, 
        user_message: str,
        user_id: UUID,
        session_id: UUID,
        message_id: UUID
    ) -> Tuple[bool, Dict]:
        """
        Analyze user message for risk indicators.
        
        Args:
            user_message: The user's message text
            user_id: User UUID
            session_id: Session UUID
            message_id: Message UUID
            
        Returns:
            Tuple of (need_crisis_mode, detection_result)
        """
        try:
            # Build messages for detector
            messages = [
                {"role": "system", "content": prompt_manager.detector_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Get AI response in JSON mode
            response, _ = await ai_client.chat_completion(
                messages=messages,
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                temperature=0.3,  # Lower temperature for more consistent classification
                json_mode=True
            )
            
            # Parse JSON response
            result = json.loads(response)
            
            # Validate response structure
            required_keys = ['risk', 'category', 'reasons', 'need_crisis_mode']
            if not all(key in result for key in required_keys):
                logger.warning(f"Invalid detector response structure: {result}")
                result = self._get_safe_default()
            
            # Log risk event if not "none"
            if result['risk'] != 'none':
                await RiskEventRepository.create(
                    user_id=user_id,
                    session_id=session_id,
                    message_id=message_id,
                    risk=result['risk'],
                    category=result['category'],
                    reasons=result['reasons'],
                    raw_detector_output=result
                )
                logger.warning(f"Risk detected: {result['risk']} - {result['category']}")
            
            return result['need_crisis_mode'], result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse detector JSON response: {e}")
            return False, self._get_safe_default()
        
        except Exception as e:
            logger.error(f"Risk detection failed: {e}")
            return False, self._get_safe_default()
    
    @staticmethod
    def _get_safe_default() -> Dict:
        """Return safe default detection result."""
        return {
            "risk": "none",
            "category": "none",
            "reasons": [],
            "need_crisis_mode": False
        }


# Global risk detector instance
risk_detector = RiskDetector()
