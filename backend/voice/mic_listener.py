import speech_recognition as sr
import logging

logger = logging.getLogger(__name__)

class MicListener:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        # Optimize for faster conversational feel
        self.recognizer.pause_threshold = 0.5 
        
    def listen_blocking(self, timeout=None, phrase_time_limit=15):
        """Listens to the microphone and returns dict with AudioData or error."""
        try:
            with sr.Microphone() as source:
                logger.info("Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                logger.info("Listening...")
                # listen handles silence and noise
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                return {"audio": audio, "error": None}
        except sr.WaitTimeoutError:
            logger.info("Listener timed out (no speech detected).")
            return {"audio": None, "error": "timeout"}
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return {"audio": None, "error": str(e)}
