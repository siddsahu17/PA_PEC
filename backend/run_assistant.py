"""
run_assistant.py — Asha Voice Assistant (Siri-style, multilingual, auto-detect)

Two modes in one file:

    Streamlit UI  (teacher / demo):
        streamlit run run_assistant.py

    Terminal loop (hands-free, for blind students):
        python run_assistant.py
        python run_assistant.py --language hi-IN
        python run_assistant.py --phrase-limit 30

Language is ALWAYS auto-detected from the student's speech — no manual picker.
If the student says "पाचन तंत्र समझाओ" the response is in Hindi.
If they say "पाचन संस्था सांगा" the response is in Marathi.
"""

from __future__ import annotations

import argparse
import base64
import logging
import os
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

load_dotenv(_BACKEND_DIR / ".env")

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("run_assistant")

# ── Detect Streamlit execution context ───────────────────────────────────────
def _in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


# ── Backend availability probe ────────────────────────────────────────────────
_BACKEND_OK = False
_BACKEND_ERR = ""
try:
    from voice.speech_to_text import SpeechToText as _STT_CLS    # noqa
    from voice.intent_router import IntentRouter as _ROUTER_CLS  # noqa
    from voice.diagram_rag_agent import DiagramRAGAgent as _RAG  # noqa
    from voice.explanation_agent import ExplanationAgent as _EXP # noqa
    from voice.text_to_speech import TextToSpeech as _TTS_CLS    # noqa
    _BACKEND_OK = True
except Exception as _e:
    _BACKEND_ERR = str(_e)


# ── Shared constants ──────────────────────────────────────────────────────────

_LANG_DISPLAY: dict[str, str] = {
    "en-IN": "English",
    "hi-IN": "हिंदी",
    "mr-IN": "मराठी",
    "bn-IN": "বাংলা",
    "ta-IN": "தமிழ்",
    "te-IN": "తెలుగు",
    "gu-IN": "ગુજરાતી",
    "kn-IN": "ಕನ್ನಡ",
}

_NOT_FOUND: dict[str, str] = {
    "en-IN": (
        "Sorry, I don't have data for that topic yet. "
        "I can describe: the digestive system, photosynthesis, the human eye, "
        "the water cycle, and the food chain."
    ),
    "hi-IN": (
        "क्षमा करें, इस विषय पर मेरे पास अभी जानकारी नहीं है। "
        "मैं पाचन तंत्र, प्रकाश संश्लेषण, मानव नेत्र, जल चक्र "
        "और खाद्य श्रृंखला के बारे में बता सकता हूँ।"
    ),
    "mr-IN": (
        "माफ करा, या विषयावर माझ्याकडे अजून माहिती नाही. "
        "मी पाचन संस्था, प्रकाश संश्लेषण, मानवी डोळा, "
        "जलचक्र आणि अन्नसाखळी सांगू शकतो."
    ),
}

_AUDIO_MIMES: dict[str, str] = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
}

SAMPLES: dict[str, list[str]] = {
    "en-IN": [
        "Explain the digestive system",
        "Describe photosynthesis",
        "Tell me about the human eye",
        "How does the water cycle work",
        "Explain the food chain",
    ],
    "hi-IN": [
        "पाचन तंत्र के बारे में बताओ",
        "प्रकाश संश्लेषण समझाओ",
        "मानव नेत्र का वर्णन करो",
        "जल चक्र कैसे काम करता है",
        "खाद्य श्रृंखला समझाओ",
    ],
    "mr-IN": [
        "पाचन संस्था सांगा",
        "प्रकाश संश्लेषण सांगा",
        "मानवी डोळा सांगा",
        "जलचक्र कसे काम करते",
        "अन्नसाखळी सांगा",
    ],
}

_MOCK_RESPONSE = (
    "Picture a grand 8-metre highway running through your body — that is the digestive system. "
    "The journey begins in the mouth. Thirty-two teeth crush and grind every bite while saliva "
    "softens the food and starts breaking down starch. The tongue rolls everything into a smooth "
    "ball and sends it down the food pipe — a 25-centimetre tube that squeezes in rhythmic waves, "
    "delivering food to the stomach in just seven seconds. The stomach, shaped like the letter J, "
    "churns your meal for two to four hours in a bath of powerful acid. That liquid then flows "
    "into the small intestine — six to seven metres of coiled tubing whose inner walls are covered "
    "in millions of tiny finger-like projections, together as large as a tennis court, absorbing "
    "every nutrient into your blood. Finally, the large intestine reclaims water, and waste is "
    "gently expelled. From first bite to last step: 24 to 72 hours of silent, perfect precision."
)


# ── Shared pipeline helper ────────────────────────────────────────────────────

def _run_pipeline(
    query: str,
    language_code: str,
    context: list[dict],
    audio_bytes: bytes | None = None,
    audio_filename: str = "audio.wav",
    mock: bool = False,
) -> dict[str, Any]:
    """
    Full STT → Route → RAG → Explain → TTS pipeline.
    Language is auto-detected from audio; `language_code` is used only as a
    fallback when STT cannot determine it (e.g. text-only queries).
    Never raises — returns error key on failure.
    """
    _blank: dict[str, Any] = {
        "transcript": "", "response_text": "", "audio_bytes": b"",
        "intent": "", "topic": None, "language": language_code, "error": None,
    }

    if mock:
        return {
            **_blank,
            "transcript": query or "Explain the digestive system",
            "response_text": _MOCK_RESPONSE,
            "intent": "diagram",
            "topic": "digestive_system",
            "language": language_code,
        }

    # Lazy agent imports (only needed in live mode)
    from voice.speech_to_text import SpeechToText
    from voice.intent_router import IntentRouter
    from voice.diagram_rag_agent import DiagramRAGAgent
    from voice.explanation_agent import ExplanationAgent
    from voice.text_to_speech import TextToSpeech

    transcript = query
    language   = language_code

    # ── Stage 1 — STT (auto-detects language from audio) ─────────────────────
    if audio_bytes:
        stt = SpeechToText()
        res = stt.transcribe(audio_bytes, filename=audio_filename)
        transcript = res.get("text", "").strip()
        language   = res.get("language_code", language_code)   # ← auto-detected
        if not transcript:
            return {**_blank, "error": res.get("error", "Could not understand speech."), "language": language}

    if not transcript:
        return {**_blank, "error": "No input provided — please speak or type."}

    # ── Stage 2 — Intent routing ──────────────────────────────────────────────
    router = IntentRouter()
    route  = router.route(transcript, context, language)
    intent = route["intent"]
    topic  = route.get("topic")
    language = route.get("language", language)   # router may refine the code

    # ── Stage 3 — RAG + Explanation ───────────────────────────────────────────
    if intent == "diagram":
        rag  = DiagramRAGAgent()
        data = rag.retrieve(transcript, topic)
        if data:
            explainer     = ExplanationAgent()
            response_text = explainer.generate(data, language)
        else:
            response_text = _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
    else:
        response_text = route.get("response", "")

    if not response_text:
        return {**_blank, "error": "Pipeline produced an empty response.", "transcript": transcript}

    # ── Stage 4 — TTS in the auto-detected language ───────────────────────────
    tts       = TextToSpeech()
    audio_out = tts.synthesize_to_bytes(response_text, language)

    return {
        "transcript":    transcript,
        "response_text": response_text,
        "audio_bytes":   audio_out,
        "intent":        intent,
        "topic":         topic,
        "language":      language,
        "error":         None,
    }


# =============================================================================
# STREAMLIT UI
# =============================================================================

def _run_streamlit() -> None:
    import streamlit as st
    import streamlit.components.v1 as components

    # ── Page config ───────────────────────────────────────────────────────────
    st.set_page_config(
        page_title="Asha — Voice Learning Assistant",
        page_icon="🎙️",
        layout="centered",
        initial_sidebar_state="expanded",
    )

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* Mic section card */
    .mic-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 20px;
        padding: 2rem 1.5rem;
        text-align: center;
        margin-bottom: 1.5rem;
        border: 1px solid #0f3460;
    }
    .mic-title {
        color: #e94560;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }
    .mic-subtitle {
        color: #a8b2c1;
        font-size: 0.85rem;
        margin-bottom: 1.2rem;
    }
    /* Language badge */
    .lang-badge {
        display: inline-block;
        background: #0f3460;
        color: #e94560;
        border-radius: 99px;
        padding: 3px 14px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    /* Chat bubbles */
    [data-testid="stChatMessageContent"] { border-radius: 14px; }
    </style>
    """, unsafe_allow_html=True)

    # ── Cached agents (one instance per Streamlit server process) ─────────────
    @st.cache_resource(show_spinner=False)
    def _get_stt():
        from voice.speech_to_text import SpeechToText
        return SpeechToText()

    @st.cache_resource(show_spinner=False)
    def _get_router():
        from voice.intent_router import IntentRouter
        return IntentRouter()

    @st.cache_resource(show_spinner=False)
    def _get_rag():
        from voice.diagram_rag_agent import DiagramRAGAgent
        return DiagramRAGAgent()

    @st.cache_resource(show_spinner=False)
    def _get_explainer():
        from voice.explanation_agent import ExplanationAgent
        return ExplanationAgent()

    @st.cache_resource(show_spinner=False)
    def _get_tts():
        from voice.text_to_speech import TextToSpeech
        return TextToSpeech()

    # ── Optimised pipeline using cached agents ────────────────────────────────
    def _pipeline_cached(
        query: str,
        language_code: str,
        context: list[dict],
        audio_bytes: bytes | None = None,
        audio_filename: str = "audio.wav",
        mock: bool = False,
    ) -> dict[str, Any]:
        _blank: dict[str, Any] = {
            "transcript": "", "response_text": "", "audio_bytes": b"",
            "intent": "", "topic": None, "language": language_code, "error": None,
        }
        if mock:
            return {**_blank, "transcript": query or "Explain the digestive system",
                    "response_text": _MOCK_RESPONSE, "intent": "diagram",
                    "topic": "digestive_system", "language": language_code}

        transcript = query
        language   = language_code

        if audio_bytes:
            res        = _get_stt().transcribe(audio_bytes, filename=audio_filename)
            transcript = res.get("text", "").strip()
            language   = res.get("language_code", language_code)
            if not transcript:
                return {**_blank, "error": res.get("error", "Could not understand speech."), "language": language}

        if not transcript:
            return {**_blank, "error": "No input provided."}

        route    = _get_router().route(transcript, context, language)
        intent   = route["intent"]
        topic    = route.get("topic")
        language = route.get("language", language)

        if intent == "diagram":
            data = _get_rag().retrieve(transcript, topic)
            response_text = (
                _get_explainer().generate(data, language)
                if data else _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
            )
        else:
            response_text = route.get("response", "")

        if not response_text:
            return {**_blank, "error": "Empty response from pipeline.", "transcript": transcript}

        audio_out = _get_tts().synthesize_to_bytes(response_text, language)
        return {
            "transcript": transcript, "response_text": response_text,
            "audio_bytes": audio_out, "intent": intent,
            "topic": topic, "language": language, "error": None,
        }

    def _autoplay(wav_bytes: bytes) -> None:
        if not wav_bytes:
            return
        b64 = base64.b64encode(wav_bytes).decode()
        components.html(
            f'<audio autoplay style="display:none">'
            f'<source src="data:audio/wav;base64,{b64}" type="audio/wav">'
            f'</audio>',
            height=0,
        )

    def _context_list(messages: list[dict], n: int = 8) -> list[dict]:
        return [
            {"role": "user" if m["role"] == "user" else "assistant", "content": m.get("text", "")}
            for m in messages[-n:]
        ]

    def _lang_label(code: str) -> str:
        name = _LANG_DISPLAY.get(code, code)
        return f'<span class="lang-badge">{name}</span>'

    def _render_msg(msg: dict) -> None:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["text"])
                if msg.get("language"):
                    st.markdown(
                        f"Detected language: {_lang_label(msg['language'])}",
                        unsafe_allow_html=True,
                    )
                if msg.get("input_audio"):
                    mime = _AUDIO_MIMES.get(Path(msg.get("audio_fn", ".wav")).suffix.lower(), "audio/wav")
                    with st.expander("Your recording", expanded=False):
                        st.audio(msg["input_audio"], format=mime)
        else:
            with st.chat_message("assistant", avatar="🎙️"):
                if msg.get("topic"):
                    label = msg["topic"].replace("_", " ").title()
                    lang  = _lang_label(msg.get("language", "en-IN"))
                    st.markdown(
                        f"Explaining **{label}** · responding in {lang}",
                        unsafe_allow_html=True,
                    )
                st.markdown(msg["text"])
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")

    # ── Session state ─────────────────────────────────────────────────────────
    if "messages"       not in st.session_state: st.session_state.messages: list[dict] = []
    if "voice_key"      not in st.session_state: st.session_state.voice_key: int = 0
    if "last_lang"      not in st.session_state: st.session_state.last_lang: str = "en-IN"
    if "latest_audio"   not in st.session_state: st.session_state.latest_audio: bytes = b""
    if "should_autoplay" not in st.session_state: st.session_state.should_autoplay: bool = False

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 🎙️ Asha")
        st.caption("NCERT Science · Voice Learning Assistant")
        st.divider()

        # Language detection notice (read-only — no manual picker)
        st.markdown("#### Language")
        detected = st.session_state.last_lang
        st.markdown(
            f"Auto-detected from your speech:  \n"
            f"**{_LANG_DISPLAY.get(detected, detected)}** `{detected}`",
            unsafe_allow_html=False,
        )
        st.caption("Speak in any language — Asha responds in the same language automatically.")

        st.divider()

        # Quick topic samples (shown in last-detected language)
        st.markdown("#### Quick Topics")
        sample_lang = detected if detected in SAMPLES else "en-IN"
        _sample_query: str | None = None
        for s in SAMPLES[sample_lang]:
            if st.button(s, key=f"sq_{s}", use_container_width=True):
                _sample_query = s

        st.divider()

        # Mock mode
        _mock: bool = st.toggle(
            "Mock Mode",
            value=not _BACKEND_OK,
            disabled=not _BACKEND_OK,
            help="Use demo data — no API keys needed.",
        )
        if not _BACKEND_OK:
            st.error(f"Backend unavailable — Mock Mode forced.\n\n`{_BACKEND_ERR[:120]}`")
        else:
            s_ok = bool(os.getenv("SARVAM_API_KEY", "").strip())
            o_ok = bool(os.getenv("OPENAI_API_KEY", "").strip())
            if not _mock:
                st.markdown(
                    f"Sarvam AI: **{'✓ connected' if s_ok else '✗ key missing'}**  \n"
                    f"OpenAI: **{'✓ connected' if o_ok else '✗ key missing'}**"
                )
                if not s_ok or not o_ok:
                    st.warning("Add missing keys to `backend/.env`")

        st.divider()
        if st.button("Clear Conversation", use_container_width=True):
            st.session_state.messages       = []
            st.session_state.latest_audio   = b""
            st.session_state.should_autoplay = False
            st.session_state.last_lang      = "en-IN"
            st.rerun()

    # ── Main area ─────────────────────────────────────────────────────────────
    st.markdown("## Asha — Voice Science Assistant")
    st.caption(
        "Speak in **English, Hindi, Marathi** (or any Indian language) — "
        "Asha detects your language and explains science diagrams in the same language, out loud."
        + ("  ·  *Mock Mode*" if _mock else "")
    )
    st.divider()

    # Mic input card
    st.markdown(
        '<div class="mic-card">'
        '<div class="mic-title">🎙️ TAP THE MIC AND SPEAK</div>'
        '<div class="mic-subtitle">Ask about: digestive system · photosynthesis · human eye · water cycle · food chain</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    _rec_audio: bytes | None = None
    _rec_fn: str = "audio.wav"
    try:
        _recorded = st.audio_input(
            "Tap to record your question",
            key=f"mic_{st.session_state.voice_key}",
        )
        if _recorded is not None:
            _rec_audio = _recorded.read()
            _rec_fn    = getattr(_recorded, "name", "audio.wav")
    except AttributeError:
        st.caption("Upgrade Streamlit for mic: `pip install -U streamlit`")
        _up = st.file_uploader(
            "Upload audio",
            type=["wav", "mp3", "ogg", "webm", "flac"],
            key=f"up_{st.session_state.voice_key}",
            label_visibility="collapsed",
        )
        if _up is not None:
            _rec_audio = _up.read()
            _rec_fn    = _up.name

    _voice_clicked = False
    if _rec_audio:
        _voice_clicked = st.button(
            "Send Voice Message",
            type="primary",
            use_container_width=True,
        )

    st.divider()

    # Chat history
    if not st.session_state.messages:
        with st.chat_message("assistant", avatar="🎙️"):
            st.markdown(
                "**Namaste! I am Asha.**  \n"
                "I am your science learning assistant.\n\n"
                "Speak to me in **any language** — English, Hindi, Marathi, or other Indian "
                "languages — and I will explain NCERT science diagrams in the same language "
                "and read the description aloud for you.\n\n"
                "Try asking about the **digestive system**, **photosynthesis**, **human eye**, "
                "**water cycle**, or **food chain**."
            )
    else:
        for msg in st.session_state.messages:
            _render_msg(msg)

    # ── Persistent audio player ───────────────────────────────────────────────
    # Rendered every run outside the query block so it survives st.rerun().
    # When should_autoplay=True (set after pipeline completes) it triggers
    # playback via both st.audio autoplay AND a hidden <audio autoplay> iframe.
    if st.session_state.latest_audio:
        if st.session_state.should_autoplay:
            st.markdown("**Now playing response:**")
            # Native Streamlit autoplay (works on Streamlit ≥ 1.16)
            try:
                st.audio(st.session_state.latest_audio, format="audio/wav", autoplay=True)
            except TypeError:
                st.audio(st.session_state.latest_audio, format="audio/wav")
            # Belt-and-suspenders: also inject HTML <audio autoplay> iframe
            _autoplay(st.session_state.latest_audio)
            # Clear flag so it doesn't autoplay again on the next natural rerun
            st.session_state.should_autoplay = False
        else:
            # Audio player shown for manual replay; no autoplay
            with st.expander("Replay last response", expanded=False):
                st.audio(st.session_state.latest_audio, format="audio/wav")

    # Text input
    _text_in = st.chat_input("Type your question, or use the mic above…")

    # ── Resolve submitted input this turn ─────────────────────────────────────
    _query: str | None = None
    _proc_audio: bytes | None = None
    _proc_fn: str = "audio.wav"
    _is_voice = False

    if _text_in and _text_in.strip():
        _query = _text_in.strip()
    elif _sample_query:
        _query = _sample_query
    elif _voice_clicked and _rec_audio:
        _proc_audio = _rec_audio
        _proc_fn    = _rec_fn
        _is_voice   = True
        _query      = "__voice__"

    # ── Execute pipeline ──────────────────────────────────────────────────────
    if _query:
        _display = "🎤 Voice message…" if _is_voice else _query
        _user_id = str(uuid.uuid4())
        _user_msg: dict[str, Any] = {
            "id": _user_id, "role": "user", "text": _display,
            "input_audio": _proc_audio, "audio_fn": _proc_fn,
            "language": st.session_state.last_lang,
        }
        st.session_state.messages.append(_user_msg)

        # Render user bubble immediately
        with st.chat_message("user"):
            st.markdown(_display)
            if _is_voice and _proc_audio:
                mime = _AUDIO_MIMES.get(Path(_proc_fn).suffix.lower(), "audio/wav")
                with st.expander("Your recording", expanded=False):
                    st.audio(_proc_audio, format=mime)

        # Asha responds
        with st.chat_message("assistant", avatar="🎙️"):
            _spinner = "Listening and understanding…" if _is_voice else "Thinking…"
            with st.spinner(_spinner):
                _ctx = _context_list(st.session_state.messages[:-1])
                _res = _pipeline_cached(
                    query          = "" if _is_voice else _query,
                    language_code  = st.session_state.last_lang,
                    context        = _ctx,
                    audio_bytes    = _proc_audio,
                    audio_filename = _proc_fn,
                    mock           = _mock,
                )

            if _res.get("error"):
                st.error(f"Sorry, I ran into a problem: {_res['error']}")
                st.session_state.messages.pop()
            else:
                # Update last detected language
                _detected_lang = _res.get("language", "en-IN")
                st.session_state.last_lang = _detected_lang

                # Update user bubble to show transcript + detected language
                if _is_voice and _res.get("transcript"):
                    st.session_state.messages[-1]["text"]     = _res["transcript"]
                    st.session_state.messages[-1]["language"] = _detected_lang

                # Render topic label + language
                if _res.get("topic"):
                    label = _res["topic"].replace("_", " ").title()
                    st.markdown(
                        f"Explaining **{label}** · responding in "
                        f"{_lang_label(_detected_lang)}",
                        unsafe_allow_html=True,
                    )
                elif _res.get("language"):
                    st.markdown(
                        f"Responding in {_lang_label(_detected_lang)}",
                        unsafe_allow_html=True,
                    )

                # Render response text
                st.markdown(_res["response_text"])

                # Persist to session state
                _asst_id = str(uuid.uuid4())
                st.session_state.messages.append({
                    "id": _asst_id, "role": "assistant",
                    "text": _res["response_text"],
                    "audio": _res["audio_bytes"],
                    "intent": _res.get("intent"),
                    "topic": _res.get("topic"),
                    "language": _detected_lang,
                })

                # Store audio for the persistent player and flag autoplay.
                # On the rerun, the persistent player (outside this block) will
                # render with autoplay=True and the audio will play.
                if _res["audio_bytes"]:
                    st.session_state.latest_audio    = _res["audio_bytes"]
                    st.session_state.should_autoplay = True
                else:
                    st.warning("No audio generated — check SARVAM_API_KEY and try again.")

                # Reset mic widget so user can record the next question
                if _is_voice:
                    st.session_state.voice_key += 1

                # Rerun: the persistent audio player will render with autoplay=True
                st.rerun()


# =============================================================================
# TERMINAL LOOP (python run_assistant.py)
# =============================================================================

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hands-free voice assistant — terminal mode.")
    p.add_argument("--language", default="en-IN",
                   choices=["en-IN", "hi-IN", "mr-IN"],
                   help="Starting language (auto-updated each turn from STT).")
    p.add_argument("--no-acknowledge", action="store_true",
                   help="Skip 'Got it, one moment' between listening and responding.")
    p.add_argument("--phrase-limit", type=float, default=25.0, metavar="SECS",
                   help="Max seconds to capture per utterance. Default: 25")
    p.add_argument("--calibrate-secs", type=float, default=1.5, metavar="SECS",
                   help="Seconds to calibrate ambient noise at startup. Default: 1.5")
    return p.parse_args()


_PHRASES: dict[str, dict[str, str]] = {
    "en-IN": {
        "welcome":     "Hello! I am Asha, your science learning assistant. Speak to me in any language and I will answer in the same language. Say goodbye to stop.",
        "acknowledge": "Got it. One moment.",
        "not_heard":   "I did not catch that. Please speak again.",
        "mic_error":   "There was a microphone error. Please check your microphone.",
        "goodbye":     "Goodbye! Keep learning!",
        "help":        "I can explain: digestive system, photosynthesis, human eye, water cycle, and food chain.",
        "api_error":   "I had trouble connecting to the server. Please check your internet.",
    },
    "hi-IN": {
        "welcome":     "नमस्ते! मैं आशा हूँ, आपका विज्ञान सहायक। किसी भी भाषा में बोलिए, मैं उसी भाषा में जवाब दूँगी। रुकने के लिए 'अलविदा' कहिए।",
        "acknowledge": "समझ गया। एक पल रुकिए।",
        "not_heard":   "मैं समझ नहीं पाई। कृपया फिर से बोलिए।",
        "mic_error":   "माइक्रोफोन में समस्या है।",
        "goodbye":     "अलविदा! पढ़ते रहिए!",
        "help":        "मैं पाचन तंत्र, प्रकाश संश्लेषण, मानव नेत्र, जल चक्र और खाद्य श्रृंखला के बारे में बता सकती हूँ।",
        "api_error":   "सर्वर से जुड़ने में समस्या हुई।",
    },
    "mr-IN": {
        "welcome":     "नमस्कार! मी आशा आहे, तुमची विज्ञान सहाय्यक। कोणत्याही भाषेत बोला, मी त्याच भाषेत उत्तर देईन. थांबण्यासाठी 'निरोप' म्हणा.",
        "acknowledge": "समजलं. एक क्षण थांबा.",
        "not_heard":   "मला ऐकू आलं नाही. कृपया पुन्हा बोला.",
        "mic_error":   "मायक्रोफोनमध्ये समस्या आहे.",
        "goodbye":     "निरोप! शिकत राहा!",
        "help":        "मी पाचन संस्था, प्रकाश संश्लेषण, मानवी डोळा, जलचक्र आणि अन्नसाखळी सांगू शकतो.",
        "api_error":   "सर्व्हरशी जोडण्यात समस्या झाली.",
    },
}

_EXIT_WORDS = {"bye", "goodbye", "exit", "quit", "stop", "अलविदा", "बंद", "निरोप", "थांबा"}
_HELP_WORDS = {"help", "topics", "मदद", "विषय", "मदत"}


def _phrase(key: str, lang: str) -> str:
    return _PHRASES.get(lang, _PHRASES["en-IN"]).get(key, _PHRASES["en-IN"][key])


# pygame helpers ──────────────────────────────────────────────────────────────

_MIXER_READY = False

def _init_pygame() -> None:
    global _MIXER_READY
    try:
        import pygame
        pygame.mixer.init(frequency=22050)
        _MIXER_READY = True
    except Exception as e:
        print(f"WARNING: pygame not available — audio disabled. ({e})")

def _play_wav(wav_bytes: bytes) -> None:
    if not _MIXER_READY or not wav_bytes:
        return
    import pygame
    tmp: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp = f.name
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
        pygame.mixer.music.unload()
    except Exception as e:
        logger.error("Playback: %s", e)
    finally:
        if tmp:
            try: os.remove(tmp)
            except Exception: pass

def _speak_terminal(tts: Any, text: str, lang: str) -> None:
    _play_wav(tts.synthesize_to_bytes(text, lang))


# Pipeline thread ─────────────────────────────────────────────────────────────

def _pipeline_worker(
    user_text: str,
    language: str,
    context: list[dict],
    result: dict,
    done: threading.Event,
) -> None:
    from voice.intent_router import IntentRouter
    from voice.diagram_rag_agent import DiagramRAGAgent
    from voice.explanation_agent import ExplanationAgent
    from voice.text_to_speech import TextToSpeech

    try:
        route    = IntentRouter().route(user_text, context, language)
        intent   = route["intent"]
        lang_out = route.get("language", language)

        if intent == "diagram":
            data = DiagramRAGAgent().retrieve(user_text, route.get("topic"))
            if data:
                response = ExplanationAgent().generate(data, lang_out)
            else:
                response = _NOT_FOUND.get(lang_out, _NOT_FOUND["en-IN"])
        else:
            response = route.get("response", "")

        audio = TextToSpeech().synthesize_to_bytes(response, lang_out)
        result.update({"success": True, "response": response, "language": lang_out,
                        "intent": intent, "audio": audio})
    except Exception as e:
        logger.error("Worker: %s", e)
        result.update({"success": False, "error": str(e)})
    finally:
        done.set()


# Terminal main ───────────────────────────────────────────────────────────────

def _terminal_main() -> None:
    args = _parse_args()

    # Fail fast on missing keys
    missing = [k for k in ("SARVAM_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"\nERROR: Missing API key(s): {', '.join(missing)}")
        print(f"Add them to {_BACKEND_DIR / '.env'} and restart.\n")
        sys.exit(1)

    try:
        import pygame
        import speech_recognition as sr
    except ImportError as e:
        print(f"ERROR: Missing package — {e}. Run: pip install pygame SpeechRecognition pyaudio")
        sys.exit(1)

    _init_pygame()

    print("\n" + "=" * 60)
    print("  Asha — NCERT Science Voice Assistant (Hands-Free)")
    print("=" * 60)
    print("  Speak in English, Hindi, or Marathi — auto-detected.")
    print("  Say 'goodbye' / 'अलविदा' / 'निरोप' to exit.")
    print("  Say 'help' / 'topics' for available topics.")
    print("=" * 60 + "\n")

    from voice.speech_to_text import SpeechToText
    from voice.text_to_speech import TextToSpeech

    stt = SpeechToText()
    tts = TextToSpeech()

    recognizer              = sr.Recognizer()
    recognizer.pause_threshold  = 1.0
    recognizer.energy_threshold = 300

    language: str      = args.language
    context: list[dict] = []
    turn = 0

    # Calibrate
    print(f"Calibrating microphone ({args.calibrate_secs}s) — stay quiet…")
    try:
        with sr.Microphone() as mic:
            recognizer.adjust_for_ambient_noise(mic, duration=args.calibrate_secs)
        print(f"Ready. Noise threshold: {recognizer.energy_threshold:.0f}\n")
    except Exception as e:
        print(f"WARNING: Calibration failed: {e}\n")

    # Welcome
    _speak_terminal(tts, _phrase("welcome", language), language)

    with sr.Microphone() as mic:
        while True:
            turn += 1
            ts = time.strftime("%H:%M:%S")
            print(f"\n[{ts}] Turn {turn}  |  Language: {_LANG_DISPLAY.get(language, language)}")
            print("─" * 50)
            print("  [Listening…]")

            # ── Listen ────────────────────────────────────────────────────────
            try:
                audio = recognizer.listen(mic, timeout=None, phrase_time_limit=args.phrase_limit)
            except Exception as e:
                print(f"  [Mic error: {e}]")
                _speak_terminal(tts, _phrase("mic_error", language), language)
                continue

            print("  [Transcribing…]")
            wav  = audio.get_wav_data()
            res  = stt.transcribe(wav, filename="audio.wav")
            text = res.get("text", "").strip()
            lang = res.get("language_code", language)

            if not text:
                print("  [No speech detected]")
                _speak_terminal(tts, _phrase("not_heard", language), language)
                continue

            language = lang
            print(f"  You  [{_LANG_DISPLAY.get(language, language)}]: {text}")

            # ── Exit / Help fast-paths ────────────────────────────────────────
            lower = text.lower()
            if any(w in lower for w in _EXIT_WORDS):
                bye = _phrase("goodbye", language)
                print(f"\n  [Exit] {bye}\n")
                _speak_terminal(tts, bye, language)
                break

            if any(w in lower for w in _HELP_WORDS):
                h = _phrase("help", language)
                print(f"  Asha : {h}")
                _speak_terminal(tts, h, language)
                context.extend([{"role": "user", "content": text}, {"role": "assistant", "content": h}])
                context = context[-20:]
                continue

            # ── Pipeline in background while acknowledgment plays ─────────────
            result: dict = {"success": False, "audio": b"", "response": "", "language": language, "intent": "chat"}
            done = threading.Event()
            threading.Thread(
                target=_pipeline_worker,
                args=(text, language, list(context), result, done),
                daemon=True,
            ).start()

            if not args.no_acknowledge:
                _speak_terminal(tts, _phrase("acknowledge", language), language)

            done.wait()

            # ── Play response ─────────────────────────────────────────────────
            if not result["success"]:
                err = _phrase("api_error", language)
                print(f"  [Error: {result.get('error', 'unknown')}]")
                _speak_terminal(tts, err, language)
            else:
                language = result["language"]
                preview  = result["response"][:120]
                preview += "…" if len(result["response"]) > 120 else ""
                print(f"  Asha [{_LANG_DISPLAY.get(language, language)}, {result['intent']}]: {preview}")
                _play_wav(result["audio"])
                context.extend([{"role": "user", "content": text}, {"role": "assistant", "content": result["response"]}])
                context = context[-20:]

    print("\nAsha stopped.\n")


# =============================================================================
# Entry point
# =============================================================================

if _in_streamlit():
    _run_streamlit()
elif __name__ == "__main__":
    _terminal_main()
