import io
import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"

_AUDIO_MIMES: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}


class SpeechToText:
    """
    Transcribes audio using Sarvam AI's Saarika STT model.
    Accepts speech_recognition.AudioData or raw bytes (WAV/MP3/OGG).
    Returns language_code detected by the model — passes it downstream
    so TTS and the explanation agent can match the student's language.
    """

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "SARVAM_API_KEY is not set — SpeechToText will return empty results. "
                "Add SARVAM_API_KEY to your .env file."
            )

    def transcribe(self, audio_data, filename: str = "audio.wav") -> dict:
        """
        Transcribe audio and return recognised text plus detected language.

        Args:
            audio_data: speech_recognition.AudioData, raw bytes, or BytesIO.
            filename:   Original filename hint (e.g. "audio.webm") — used to
                        set the correct MIME type in the Sarvam API request.

        Returns:
            {
                "text": str,          # transcribed text, empty string on failure
                "language_code": str, # e.g. "hi-IN", "mr-IN", "en-IN"
                "confidence": float,  # 0.0–1.0
                "error": str | None   # set only on failure
            }
        """
        if not audio_data:
            return self._empty("no audio data provided")

        # --- resolve audio bytes --------------------------------------------------
        try:
            if hasattr(audio_data, "get_wav_data"):
                wav_bytes = audio_data.get_wav_data()
            elif isinstance(audio_data, (bytes, bytearray)):
                wav_bytes = bytes(audio_data)
            else:
                return self._empty(f"unsupported audio type: {type(audio_data)}")
        except Exception as e:
            return self._empty(f"failed to read audio data: {e}")

        # --- call Sarvam AI -------------------------------------------------------
        ext = os.path.splitext(filename)[1].lower() or ".wav"
        mime_type = _AUDIO_MIMES.get(ext, "audio/wav")

        try:
            response = requests.post(
                SARVAM_STT_URL,
                headers={"api-subscription-key": self.api_key},
                files={
                    "file": (filename, io.BytesIO(wav_bytes), mime_type),
                },
                data={
                    "model": "saarika:v2.5",
                    "with_timestamps": "false",
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            transcript = result.get("transcript", "").strip()
            language_code = result.get("language_code", "en-IN")

            logger.info(
                "Sarvam STT: [%s] '%s'",
                language_code,
                transcript[:60] + "..." if len(transcript) > 60 else transcript,
            )
            return {
                "text": transcript,
                "language_code": language_code,
                "confidence": 0.95,
                "error": None,
            }

        except requests.exceptions.Timeout:
            return self._empty("Sarvam STT request timed out", log_level="error")
        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = e.response.text[:200]
            except Exception:
                pass
            return self._empty(
                f"Sarvam STT HTTP {e.response.status_code}: {body}",
                log_level="error",
            )
        except Exception as e:
            return self._empty(str(e), log_level="error")

    # ------------------------------------------------------------------

    @staticmethod
    def _empty(reason: str, log_level: str = "warning") -> dict:
        getattr(logger, log_level)("SpeechToText: %s", reason)
        return {
            "text": "",
            "language_code": "en-IN",
            "confidence": 0.0,
            "error": reason,
        }
