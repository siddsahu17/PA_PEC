import os
import tempfile
from gtts import gTTS
import pygame
import logging
import time

logger = logging.getLogger(__name__)

class TextToSpeech:
    def __init__(self):
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init()
        except pygame.error as e:
            logger.error(f"Failed to initialize pygame mixer: {e}")

    def speak(self, text: str):
        """Converts text to speech and plays it immediately."""
        if not text or not text.strip():
            return
            
        temp_path = None
        try:
            logger.info("Generating TTS...")
            tts = gTTS(text=text, lang='en', slow=False)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name
            
            tts.save(temp_path)
            
            logger.info("Playing audio...")
            pygame.mixer.music.load(temp_path)
            pygame.mixer.music.play()
            
            # Block until playback is finished
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            # Unload audio so the file can be deleted on Windows
            pygame.mixer.music.unload()
            
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    logger.debug(f"Failed to delete temp audio file {temp_path}: {e}")
