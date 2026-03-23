import logging
from app.services.audio_service import audio_service_instance

logger = logging.getLogger("assistant_backend.voice_agent")

class VoiceAgent:
    async def speech_to_text(self, audio_path: str) -> str:
        logger.info(f"Voice Agent transcribing audio: {audio_path}")
        try:
            transcript = await audio_service_instance.transcribe(audio_path)
            return transcript
        except Exception as e:
            logger.error(f"STT failed: {e}")
            raise ValueError("Failed to transcribe speech to text.")

    async def text_to_speech(self, text: str) -> str:
        logger.info("Voice Agent synthesizing speech")
        try:
            audio_output_path = await audio_service_instance.synthesize(text)
            return audio_output_path
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise ValueError("Failed to synthesize text to speech.")
