import json
import logging
from typing import Dict, Any

from app.services.openai_service import OpenAIService
from app.core.prompts import VISION_SYSTEM_PROMPT

logger = logging.getLogger("assistant_backend.vision_agent")

class VisionAgent:
    async def analyze(self, image_path: str) -> Dict[str, Any]:
        logger.info(f"Vision Agent analyzing image: {image_path}")
        try:
            raw_response = await OpenAIService.analyze_image_with_vision(image_path, VISION_SYSTEM_PROMPT)
            # Parse the JSON
            structured_data = json.loads(raw_response)
            return structured_data
        except Exception as e:
            logger.error(f"Vision Analysis Failed: {e}")
            raise ValueError("Failed to analyze image with Vision API.")
