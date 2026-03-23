import logging
from typing import Dict, Any

from app.agents.vision_agent import VisionAgent
from app.agents.explanation_agent import ExplanationAgent
from app.agents.braille_agent import BrailleAgent
from app.agents.voice_agent import VoiceAgent

logger = logging.getLogger("assistant_backend.pipeline")

class AssistantPipeline:
    def __init__(self):
        self.vision_agent = VisionAgent()
        self.explanation_agent = ExplanationAgent()
        self.braille_agent = BrailleAgent()
        self.voice_agent = VoiceAgent()

    async def process_image(self, image_path: str) -> Dict[str, Any]:
        logger.info(f"Pipeline started for image: {image_path}")

        # 1. Vision Agent predicts structural JSON
        structured_data = await self.vision_agent.analyze(image_path)
        
        # 2. Explanation Agent generates descriptive text
        explanation_text = await self.explanation_agent.generate_explanation(structured_data)
        
        # 3. Braille Agent transcribes description to Braille
        braille_text = await self.braille_agent.transcribe(explanation_text)
        
        return {
            "structured": structured_data,
            "explanation": explanation_text,
            "braille": braille_text
        }

    async def process_voice(self, audio_path: str, session_id: str) -> Dict[str, Any]:
        logger.info(f"Pipeline started for voice input: {audio_path}")
        
        # 1. Voice Agent -> STT
        transcribed_text = await self.voice_agent.speech_to_text(audio_path)
        
        # 2. Generate conversational response based on memory and transcribed text
        # To avoid circular imports, logic is encapsulated in the agents or services
        response_text = await self.explanation_agent.generate_conversational_response(transcribed_text, session_id)
        
        # 3. Voice Agent -> TTS
        audio_response_path = await self.voice_agent.text_to_speech(response_text)
        
        return {
            "transcription": transcribed_text,
            "response": response_text,
            "audio_url": audio_response_path # In production this would be an accessible URL/S3 link
        }
