import speech_recognition as sr
import os
import logging
import tempfile
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SpeechToText:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def transcribe(self, audio_data: sr.AudioData):
        """Converts AudioData to text, using official OpenAI Whisper API if key is available, else falling back to Google free."""
        if not audio_data:
            return {"text": "", "confidence": 0.0}
            
        try:
            if self.client:
                # Highly accurate Whisper API via native client
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_wav.write(audio_data.get_wav_data())
                    temp_wav_path = temp_wav.name
                
                with open(temp_wav_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                os.remove(temp_wav_path)
                return {"text": transcript.text.strip(), "confidence": 0.9}
            else:
                # Fallback to Google STT (Free tier)
                text = self.recognizer.recognize_google(audio_data)
                return {"text": text.strip(), "confidence": 0.8}
                
        except sr.UnknownValueError:
            logger.warning("STT could not understand audio")
            return {"text": "", "confidence": 0.0}
        except sr.RequestError as e:
            logger.error(f"STT Request Error: {e}")
            return {"text": "", "confidence": 0.0}
        except Exception as e:
            logger.error(f"Unexpected STT Error: {e}")
            return {"text": "", "confidence": 0.0}
