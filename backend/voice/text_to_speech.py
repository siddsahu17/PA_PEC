import base64
import io
import logging
import os
import tempfile
import wave

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

# Maps language code -> (speaker, sample_rate).
# Speakers are from Sarvam's Bulbul v1 voice roster.
_LANG_CONFIG: dict[str, tuple[str, int]] = {
    "en-IN": ("anushka", 22050),
    "hi-IN": ("anushka", 22050),
    "mr-IN": ("anushka", 22050),
    "bn-IN": ("anushka", 22050),
    "ta-IN": ("anushka", 22050),
    "te-IN": ("anushka", 22050),
    "gu-IN": ("anushka", 22050),
    "kn-IN": ("anushka", 22050),
}

# Sarvam TTS accepts at most 500 characters per request.
_MAX_CHARS = 500


class TextToSpeech:
    """
    Converts text to speech using Sarvam AI's Bulbul TTS model.
    Handles multi-language output (English, Hindi, Marathi, …) and
    automatically splits long texts into chunks before synthesis.
    """

    def __init__(self):
        self.api_key = os.getenv("SARVAM_API_KEY", "")
        if not self.api_key:
            logger.warning(
                "SARVAM_API_KEY is not set — TextToSpeech will be silent. "
                "Add SARVAM_API_KEY to your .env file."
            )
        self._mixer_ready = False
        self._init_pygame()

    def _init_pygame(self):
        try:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050)
            self._mixer_ready = True
        except Exception as e:
            logger.warning("pygame mixer not available: %s — audio playback disabled", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def speak(self, text: str, language_code: str = "en-IN") -> None:
        """
        Synthesise text and play it through the system speakers.
        Blocks until all audio has finished playing.
        """
        if not text or not text.strip():
            return
        for chunk in self._chunk_text(text):
            wav_bytes = self._synthesize_chunk(chunk, language_code)
            if wav_bytes:
                self._play_wav(wav_bytes)

    def synthesize_to_bytes(self, text: str, language_code: str = "en-IN") -> bytes:
        """
        Return a single valid WAV file (bytes) for the full text.
        Multiple chunks are merged via their PCM frames so the output
        is always a properly-headed WAV that browsers can decode.
        """
        if not text or not text.strip():
            return b""
        wavs = [
            wav
            for chunk in self._chunk_text(text)
            if (wav := self._synthesize_chunk(chunk, language_code))
        ]
        if not wavs:
            return b""
        if len(wavs) == 1:
            return wavs[0]
        return self._merge_wavs(wavs)

    @staticmethod
    def _merge_wavs(wav_list: list[bytes]) -> bytes:
        """Concatenate a list of WAV byte-strings into one valid WAV."""
        frames = b""
        params = None
        for raw in wav_list:
            with wave.open(io.BytesIO(raw)) as wf:
                if params is None:
                    params = wf.getparams()
                frames += wf.readframes(wf.getnframes())
        buf = io.BytesIO()
        with wave.open(buf, "wb") as out:
            out.setparams(params)
            out.writeframes(frames)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Chunking
    # ------------------------------------------------------------------

    def _chunk_text(self, text: str) -> list[str]:
        """Split text at sentence boundaries to stay within _MAX_CHARS."""
        if len(text) <= _MAX_CHARS:
            return [text]

        # Normalise Devanagari full stop (।) to ASCII period for splitting
        normalised = text.replace("।", ".")
        chunks: list[str] = []
        current = ""

        for sentence in normalised.split("."):
            sentence = sentence.strip()
            if not sentence:
                continue
            candidate = f"{current}. {sentence}".strip() if current else sentence
            if len(candidate) <= _MAX_CHARS:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # If a single sentence exceeds the limit, hard-split it
                while len(sentence) > _MAX_CHARS:
                    chunks.append(sentence[:_MAX_CHARS])
                    sentence = sentence[_MAX_CHARS:]
                current = sentence

        if current:
            chunks.append(current)
        return chunks

    # ------------------------------------------------------------------
    # Synthesis
    # ------------------------------------------------------------------

    def _synthesize_chunk(self, text: str, language_code: str) -> bytes | None:
        """Call Sarvam TTS for a single chunk. Returns WAV bytes or None."""
        speaker, sample_rate = _LANG_CONFIG.get(language_code, ("anushka", 22050))
        try:
            response = requests.post(
                SARVAM_TTS_URL,
                headers={
                    "api-subscription-key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": [text],
                    "target_language_code": language_code,
                    "speaker": speaker,
                    "model": "bulbul:v1",
                    "pitch": 0,
                    "pace": 0.9,        # slightly slower for accessibility
                    "loudness": 1.5,
                    "speech_sample_rate": sample_rate,
                    "enable_preprocessing": True,
                },
                timeout=30,
            )
            response.raise_for_status()
            audios = response.json().get("audios", [])
            if not audios:
                logger.error("Sarvam TTS returned empty audios list")
                return None
            return base64.b64decode(audios[0])

        except requests.exceptions.Timeout:
            logger.error("Sarvam TTS request timed out")
        except requests.exceptions.HTTPError as e:
            body = ""
            try:
                body = e.response.text[:200]
            except Exception:
                pass
            logger.error("Sarvam TTS HTTP %s: %s", e.response.status_code, body)
        except Exception as e:
            logger.error("Sarvam TTS synthesis failed: %s", e)
        return None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _play_wav(self, wav_bytes: bytes) -> None:
        """Write WAV bytes to a temp file and play via pygame."""
        if not self._mixer_ready:
            logger.debug("pygame not ready — skipping playback")
            return
        import pygame

        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            pygame.mixer.music.unload()     # required on Windows before file deletion

        except Exception as e:
            logger.error("Audio playback failed: %s", e)
        finally:
            if tmp_path:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
