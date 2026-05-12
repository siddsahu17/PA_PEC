import logging
from typing import Generator

from .conversation_manager import ConversationManager
from .diagram_rag_agent import DiagramRAGAgent
from .explanation_agent import ExplanationAgent
from .intent_router import IntentRouter
from .mic_listener import MicListener
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Language-aware "not found" messages for diagram retrieval failures
# -----------------------------------------------------------------------
_NOT_FOUND: dict[str, str] = {
    "en-IN": (
        "Sorry, I don't have data for that topic yet. "
        "I can currently explain: digestive system, photosynthesis, human eye, "
        "water cycle, and food chain."
    ),
    "hi-IN": (
        "क्षमा करें, इस विषय पर मेरे पास अभी जानकारी नहीं है। "
        "मैं अभी इनके बारे में बता सकता हूँ: पाचन तंत्र, प्रकाश संश्लेषण, "
        "मानव नेत्र, जल चक्र और खाद्य श्रृंखला।"
    ),
    "mr-IN": (
        "माफ करा, या विषयावर माझ्याकडे अजून माहिती नाही. "
        "मी आत्ता यांबद्दल सांगू शकतो: पाचन संस्था, प्रकाश संश्लेषण, "
        "मानवी डोळा, जलचक्र आणि अन्नसाखळी."
    ),
}


class VoiceAssistant:
    """
    Orchestrates the full multilingual voice pipeline:

        Mic → Sarvam STT → IntentRouter → DiagramRAGAgent → ExplanationAgent
                                        ↘ ConversationManager (chat)
        All paths → Sarvam TTS → Speakers

    run_step_by_step() is a generator that yields status dicts so the
    Streamlit UI can display real-time progress.
    """

    def __init__(self):
        self.mic = MicListener()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.router = IntentRouter()
        self.convo = ConversationManager()
        self.rag = DiagramRAGAgent()
        self.explainer = ExplanationAgent()

    def run_step_by_step(self) -> Generator[dict, None, None]:
        """
        Execute one full conversational turn and stream status updates.

        Yields dicts with at minimum {"status": str, "message": str}.
        Additional keys depend on the status:
          - "user_spoken"        → also has "text", "language"
          - "assistant_responded"→ also has "text", "intent", "language"
        """

        # ----------------------------------------------------------------
        # Step 1 — Listen
        # ----------------------------------------------------------------
        yield {"status": "listening", "message": "Listening for speech…"}

        mic_res = self.mic.listen_blocking(timeout=5, phrase_time_limit=20)

        if mic_res["error"] == "timeout":
            yield {"status": "idle", "message": "No speech detected. Waiting…"}
            return
        if mic_res["error"]:
            yield {
                "status": "error",
                "message": f"Microphone error: {mic_res['error']}. Is your mic connected?",
            }
            return

        audio = mic_res["audio"]

        # ----------------------------------------------------------------
        # Step 2 — Transcribe with Sarvam STT
        # ----------------------------------------------------------------
        yield {"status": "transcribing", "message": "Transcribing speech…"}

        stt_result = self.stt.transcribe(audio)
        user_text = stt_result.get("text", "").strip()
        language_code = stt_result.get("language_code", "en-IN")

        if not user_text:
            yield {"status": "error", "message": "Could not transcribe audio. Please speak clearly."}
            return

        logger.info("User [%s]: %s", language_code, user_text)
        self.convo.add_user_message(user_text)
        yield {
            "status": "user_spoken",
            "text": user_text,
            "language": language_code,
            "message": "Thinking…",
        }

        # ----------------------------------------------------------------
        # Step 3 — Route intent
        # ----------------------------------------------------------------
        context = self.convo.get_context()
        route = self.router.route(user_text, context, language_code)

        intent = route["intent"]
        language = route.get("language", language_code)

        # ----------------------------------------------------------------
        # Step 4 — Handle each intent
        # ----------------------------------------------------------------
        assistant_text = ""

        if intent == "diagram":
            topic_hint = route.get("topic")
            yield {
                "status": "retrieving_diagram",
                "message": f"Searching for '{topic_hint}'…",
                "intent": intent,
            }

            diagram_data = self.rag.retrieve(user_text, topic_hint)

            if diagram_data is None:
                assistant_text = _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
            else:
                yield {
                    "status": "generating_description",
                    "message": f"Crafting description in {language}…",
                    "intent": intent,
                }
                assistant_text = self.explainer.generate(diagram_data, language)

        elif intent == "youtube":
            assistant_text = route["response"]

        else:  # chat
            assistant_text = route["response"]

        # ----------------------------------------------------------------
        # Step 5 — Update memory and yield the response
        # ----------------------------------------------------------------
        self.convo.add_assistant_message(assistant_text)
        logger.info("Assistant [%s, %s]: %s", intent, language, assistant_text[:80])

        yield {
            "status": "assistant_responded",
            "text": assistant_text,
            "intent": intent,
            "language": language,
            "message": "Generating voice…",
        }

        # ----------------------------------------------------------------
        # Step 6 — Speak with Sarvam TTS
        # ----------------------------------------------------------------
        self.tts.speak(assistant_text, language)

        yield {"status": "done", "message": "Turn complete."}

    def process_query(
        self,
        audio_bytes: bytes | None = None,
        text_query: str | None = None,
        language_code: str = "en-IN",
        audio_filename: str = "audio.wav",
    ) -> dict:
        """
        Single-call pipeline entry point — no microphone required.
        Used by the Streamlit dashboard and FastAPI endpoints.

        Args:
            audio_bytes:    Raw audio bytes (WAV/MP3/WebM etc.) from a file upload.
            text_query:     Plain-text query (used when audio_bytes is None).
            language_code:  Fallback language when STT cannot detect it.
            audio_filename: Original filename for MIME-type detection by STT.

        Returns a dict with keys:
            success, transcript, language_detected, intent, topic,
            retrieved_data, response_text, audio_bytes, error
        """
        result: dict = {
            "success": False,
            "transcript": "",
            "language_detected": language_code,
            "intent": "chat",
            "topic": None,
            "retrieved_data": None,
            "response_text": "",
            "audio_bytes": b"",
            "error": None,
        }

        # Step 1 — STT
        if audio_bytes:
            stt_res = self.stt.transcribe(audio_bytes, filename=audio_filename)
            result["transcript"] = stt_res.get("text", "").strip()
            result["language_detected"] = stt_res.get("language_code", language_code)
            if not result["transcript"]:
                result["error"] = stt_res.get("error", "STT returned empty transcript")
                return result
        else:
            result["transcript"] = (text_query or "").strip()
            if not result["transcript"]:
                result["error"] = "No input provided (audio_bytes and text_query are both empty)"
                return result

        language = result["language_detected"]

        # Step 2 — Intent routing
        route = self.router.route(result["transcript"], self.convo.get_context(), language)
        result["intent"] = route["intent"]
        result["topic"] = route.get("topic")

        # Step 3 — RAG + Explanation
        if result["intent"] == "diagram":
            result["retrieved_data"] = self.rag.retrieve(result["transcript"], result["topic"])
            if result["retrieved_data"]:
                result["response_text"] = self.explainer.generate(result["retrieved_data"], language)
            else:
                result["response_text"] = _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
        else:
            result["response_text"] = route.get("response", "")

        self.convo.add_user_message(result["transcript"])
        self.convo.add_assistant_message(result["response_text"])

        # Step 4 — TTS
        if result["response_text"]:
            result["audio_bytes"] = self.tts.synthesize_to_bytes(result["response_text"], language)

        result["success"] = True
        return result


# ---------------------------------------------------------------------------
# Module-level convenience wrapper for programmatic / CLI use
# ---------------------------------------------------------------------------

def process_voice_query(
    audio_bytes: bytes | None = None,
    text_query: str | None = None,
    language_code: str = "en-IN",
    audio_filename: str = "audio.wav",
) -> dict:
    """
    Convenience function — creates a VoiceAssistant and runs one pipeline turn.
    Suitable for scripts, tests, and FastAPI route handlers.
    For repeated calls, instantiate VoiceAssistant() once and call process_query().
    """
    return VoiceAssistant().process_query(audio_bytes, text_query, language_code, audio_filename)
