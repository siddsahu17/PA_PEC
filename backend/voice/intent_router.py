import json
import logging
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

_YOUTUBE_RE = re.compile(
    r"(https?://(?:www\.)?youtu(?:be\.com|\.be)[^\s]+)", re.IGNORECASE
)

# -----------------------------------------------------------------------
# Classifier prompt
# -----------------------------------------------------------------------
_CLASSIFIER_SYSTEM = """You are an intent classifier for a voice assistant that helps visually impaired \
students (Classes 5–8) explore NCERT science diagrams in their native Indian language.

Analyse the user message and return ONLY a JSON object with these exact keys:

{
  "intent": "diagram" | "chat" | "youtube",
  "topic": "<snake_case diagram key or null>",
  "language": "<en-IN | hi-IN | mr-IN>"
}

INTENT RULES:
- "diagram"  → user asks to explain, describe, understand, or visualise a scientific concept or diagram
               (digestive system, photosynthesis, human eye, water cycle, food chain, solar system, etc.)
- "youtube"  → user wants to open or play a YouTube video
- "chat"     → anything else (greetings, follow-up questions, general science chat)

TOPIC RULES (only for "diagram" intent):
- Convert the topic to snake_case (e.g. "digestive_system", "human_eye", "water_cycle")
- Common NCERT topics: digestive_system, photosynthesis, human_eye, water_cycle, food_chain,
  solar_system, human_heart, cell_structure, nervous_system, respiratory_system
- If uncertain about the exact topic, still return your best guess in snake_case
- For non-diagram intents, set topic to null

LANGUAGE RULES (use the STT language hint; override only if the text itself is clearly a different language):
- Devanagari script or typical Hindi vocabulary → "hi-IN"
- Marathi-specific words (आहे, आहात, करा, मराठी) → "mr-IN"
- Everything else → "en-IN"

Return ONLY the JSON object — no markdown, no explanation."""


class IntentRouter:
    """
    Detects diagram intent, topic, and language from a user utterance.
    Separates intent classification from response generation so each concern
    stays testable and replaceable independently.
    """

    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    # ------------------------------------------------------------------
    # Primary routing method
    # ------------------------------------------------------------------

    def route(self, text: str, context: list, language_code: str = "en-IN") -> dict:
        """
        Classify intent and return routing metadata.

        Args:
            text:          The user's transcribed utterance.
            context:       Full conversation context list (from ConversationManager).
            language_code: Language code detected by Sarvam STT (e.g. 'hi-IN').

        Returns:
            {
                "intent":   "diagram" | "chat" | "youtube",
                "topic":    str | None,   # snake_case diagram key
                "language": str,          # language code to use downstream
                "response": str,          # only populated for "chat" intent
            }
        """
        if not text.strip():
            return self._chat_result("", language_code)

        # Fast path: YouTube link/mention
        if _YOUTUBE_RE.search(text) or "youtube" in text.lower():
            url_match = _YOUTUBE_RE.search(text)
            url = url_match.group(1) if url_match else None
            return {
                "intent": "youtube",
                "topic": None,
                "language": language_code,
                "response": (
                    f"I detected a YouTube URL: {url}. Please use the main app to view it."
                    if url else
                    "I heard 'YouTube' but didn't catch the link. Could you share the URL?"
                ),
            }

        # LLM classification
        classification = self._classify(text, language_code)
        intent = classification.get("intent", "chat")
        topic = classification.get("topic")
        language = classification.get("language", language_code)

        if intent == "diagram":
            return {"intent": "diagram", "topic": topic, "language": language, "response": ""}

        # Chat: generate response immediately so VoiceAssistant can use it
        response_text = self._chat_response(text, context, language)
        return {
            "intent": "chat",
            "topic": None,
            "language": language,
            "response": response_text,
        }

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify(self, text: str, language_hint: str) -> dict:
        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": _CLASSIFIER_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"STT language hint: {language_hint}\n"
                            f"User message: {text}"
                        ),
                    },
                ],
                max_tokens=120,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return json.loads(completion.choices[0].message.content)
        except Exception as e:
            logger.error("Intent classification failed: %s", e)
            return {"intent": "chat", "topic": None, "language": language_hint}

    # ------------------------------------------------------------------
    # Chat response generation
    # ------------------------------------------------------------------

    def _chat_response(self, text: str, context: list, language: str) -> str:
        _LANG_NAMES = {"en-IN": "English", "hi-IN": "Hindi", "mr-IN": "Marathi"}
        lang_name = _LANG_NAMES.get(language, "English")

        # Replace generic system prompt with a language-aware one
        system_msg = {
            "role": "system",
            "content": (
                f"You are a helpful, friendly science tutor for visually impaired students "
                f"(Classes 5–8). Respond in {lang_name}. "
                f"Keep answers concise and suitable for spoken delivery — no bullet points, "
                f"no markdown, no formatting. Speak directly to the student."
            ),
        }
        # Replace the first element of context (original system prompt) with ours
        messages = [system_msg] + [m for m in context if m.get("role") != "system"]
        messages.append({"role": "user", "content": text})

        try:
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=250,
                temperature=0.7,
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Chat response generation failed: %s", e)
            _ERRORS = {
                "hi-IN": "माफ़ करें, मैं अभी जवाब नहीं दे पा रहा।",
                "mr-IN": "माफ करा, मी आत्ता उत्तर देऊ शकत नाही.",
            }
            return _ERRORS.get(language, "Sorry, I'm having trouble responding right now.")

    # ------------------------------------------------------------------

    @staticmethod
    def _chat_result(text: str, language_code: str) -> dict:
        return {"intent": "chat", "topic": None, "language": language_code, "response": text}
