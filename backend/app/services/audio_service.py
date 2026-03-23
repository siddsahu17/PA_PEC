import whisper
import os
import uuid
import logging
from app.config.settings import settings
from app.services.openai_service import client

logger = logging.getLogger("assistant_backend.audio_service")

class AudioService:
    def __init__(self):
        # We load whisper once. Using default 'base' model unless configured otherwise.
        try:
            self.model = whisper.load_model(settings.WHISPER_MODEL)
            logger.info(f"Loaded whisper model: {settings.WHISPER_MODEL}")
        except Exception as e:
            logger.warning(f"Failed to load whisper model via local dependency (might need FFmpeg): {e}")
            self.model = None

    async def transcribe(self, audio_path: str) -> str:
        if self.model:
            logger.info("Using local Whisper for STT")
            result = self.model.transcribe(audio_path)
            return result["text"].strip()
        else:
            # Fallback to OpenAI API if local whisper fails to load
            logger.info("Using OpenAI Whisper API for STT fallback")
            with open(audio_path, "rb") as audio_file:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            return transcript.text

    async def synthesize(self, text: str) -> str:
        """
        Uses OpenAI TTS for high-quality voice synthesis
        """
        file_name = f"{uuid.uuid4()}.mp3"
        output_path = os.path.join(settings.TEMP_DIR, file_name)
        
        response = await client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
        )
        
        # Async write to file using aiofiles can be used, but OpenAI client streams
        response.stream_to_file(output_path)
        return output_path

audio_service_instance = AudioService()
