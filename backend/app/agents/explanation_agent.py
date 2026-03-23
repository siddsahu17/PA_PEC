import json
import logging
from typing import Dict, Any

from app.services.openai_service import OpenAIService
from app.core.prompts import EXPLANATION_SYSTEM_PROMPT
from app.core.memory import memory

logger = logging.getLogger("assistant_backend.explanation_agent")

class ExplanationAgent:
    async def generate_explanation(self, structured_data: Dict[str, Any]) -> str:
        logger.info("Explanation agent mapping data to descriptive text")
        data_str = json.dumps(structured_data, indent=2)
        
        prompt = f"Given this parsed diagram structure, generate the detailed narration:\n{data_str}"
        
        try:
            explanation = await OpenAIService.generate_completion(EXPLANATION_SYSTEM_PROMPT, prompt)
            return explanation.strip()
        except Exception as e:
            logger.error(f"Explanation Generation Failed: {e}")
            raise ValueError("Failed to generate explanation text.")

    async def generate_conversational_response(self, user_text: str, session_id: str) -> str:
        logger.info(f"Generating conversational response for session {session_id}")
        
        # Add user's message to memory
        memory.add_message(session_id, "user", user_text)
        
        # Build conversation context
        history = memory.get_history(session_id)
        
        # We can format this into a big prompt, or use standard conversational schemas.
        # For simplicity, we'll format the history as a string user_prompt.
        history_str = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in history])
        context_prompt = f"Here is the conversation history:\n{history_str}\n\nAgent:"
        
        try:
            response = await OpenAIService.generate_completion(EXPLANATION_SYSTEM_PROMPT, context_prompt)
            # Save assistant response
            memory.add_message(session_id, "assistant", response)
            return response.strip()
        except Exception as e:
            logger.error(f"Conversational Generation Failed: {e}")
            raise ValueError("Failed to generate conversational response.")
