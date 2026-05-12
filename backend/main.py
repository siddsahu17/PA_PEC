"""
Asha — Conversational Learning Voice Assistant
A voice chatbot for visually impaired NCERT science students (Classes 5–8).

Run from the backend/ directory:
    streamlit run main.py
"""

import base64
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

# ── sys.path — ensure voice.* is importable ───────────────────────────────────
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# ── Backend availability probe ────────────────────────────────────────────────
_BACKEND_OK: bool = False
_BACKEND_ERR: str = ""
try:
    # Import each agent individually so a missing optional dep (e.g. pygame,
    # speech_recognition) only triggers mock mode, not a hard crash.
    from voice.speech_to_text import SpeechToText as _STT_CLS       # noqa
    from voice.intent_router import IntentRouter as _ROUTER_CLS     # noqa
    from voice.diagram_rag_agent import DiagramRAGAgent as _RAG_CLS # noqa
    from voice.explanation_agent import ExplanationAgent as _EXP_CLS# noqa
    from voice.text_to_speech import TextToSpeech as _TTS_CLS       # noqa
    _BACKEND_OK = True
except Exception as _e:
    _BACKEND_ERR = str(_e)


# ── Lazy cached agent constructors ───────────────────────────────────────────
# Each agent is created once per Streamlit session and reused across reruns.

@st.cache_resource(show_spinner=False)
def _stt():
    from voice.speech_to_text import SpeechToText
    return SpeechToText()

@st.cache_resource(show_spinner=False)
def _router():
    from voice.intent_router import IntentRouter
    return IntentRouter()

@st.cache_resource(show_spinner=False)
def _rag():
    from voice.diagram_rag_agent import DiagramRAGAgent
    return DiagramRAGAgent()

@st.cache_resource(show_spinner=False)
def _explainer():
    from voice.explanation_agent import ExplanationAgent
    return ExplanationAgent()

@st.cache_resource(show_spinner=False)
def _tts():
    from voice.text_to_speech import TextToSpeech
    return TextToSpeech()


# ── Constants ─────────────────────────────────────────────────────────────────

LANGUAGES: dict[str, str] = {
    "English  (en-IN)": "en-IN",
    "Hindi — हिंदी  (hi-IN)": "hi-IN",
    "Marathi — मराठी  (mr-IN)": "mr-IN",
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

_NOT_FOUND: dict[str, str] = {
    "en-IN": (
        "Sorry, I don't have data for that topic yet. "
        "I can describe: the digestive system, photosynthesis, the human eye, "
        "the water cycle, and the food chain. Ask me about any of those!"
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

# Mock response used in offline / Mock Mode
_MOCK_SCRIPT = (
    "Picture a grand 8-metre highway running through your body — that is the digestive system. "
    "The journey begins in the mouth. Thirty-two teeth, arranged in a curve like a mortar and pestle, "
    "crush and grind every bite while saliva softens the food and starts breaking down starch. "
    "The tongue rolls everything into a smooth ball and sends it down the food pipe. "
    "This 25-centimetre tube squeezes in rhythmic waves — like pressing toothpaste from the top "
    "of the tube downward — and the food reaches the stomach in just seven seconds. "
    "The stomach is a muscular pouch shaped like the letter J. Its three layers of muscle churn "
    "your meal for two to four hours in a bath of powerful acid, turning it into a smooth liquid. "
    "That liquid flows into the small intestine — six to seven metres of tubing coiled tightly in "
    "your belly. Run your fingers along velvet and imagine millions of tiny finger-like projections: "
    "that is the texture of the inner wall. Every single projection absorbs nutrients directly into "
    "your blood, and together they cover an area as large as a full tennis court. "
    "Finally, the large intestine reclaims water, and waste is gently expelled. "
    "From the first bite to the very last step, this extraordinary journey takes 24 to 72 hours — "
    "your body working in perfect, silent precision every single day."
)


# ── Core helpers ──────────────────────────────────────────────────────────────

def _autoplay(wav_bytes: bytes) -> None:
    """Inject a hidden HTML audio element that plays automatically on page load."""
    if not wav_bytes:
        return
    b64 = base64.b64encode(wav_bytes).decode()
    components.html(
        f'<audio autoplay style="display:none">'
        f'<source src="data:audio/wav;base64,{b64}" type="audio/wav">'
        f'</audio>',
        height=0,
    )


def _context_from_history(messages: list[dict], n: int = 8) -> list[dict]:
    """Convert the last n chat messages to OpenAI-style context dicts."""
    out = []
    for msg in messages[-n:]:
        role = "user" if msg["role"] == "user" else "assistant"
        out.append({"role": role, "content": msg.get("text", "")})
    return out


def _run_pipeline(
    query: str,
    language_code: str,
    context: list[dict],
    audio_bytes: bytes | None = None,
    audio_filename: str = "audio.wav",
    mock: bool = False,
) -> dict[str, Any]:
    """
    Execute the full STT → Route → RAG → Explain → TTS pipeline.
    Returns a normalised result dict — never raises.
    """
    _blank = {"transcript": "", "response_text": "", "audio_bytes": b"",
              "intent": "", "topic": None, "language": language_code, "error": None}

    if mock:
        return {
            **_blank,
            "transcript": query or "Explain the digestive system",
            "response_text": _MOCK_SCRIPT,
            "intent": "diagram",
            "topic": "digestive_system",
            "language": language_code,
        }

    transcript = query
    language = language_code

    # Stage 1 — STT
    if audio_bytes:
        res = _stt().transcribe(audio_bytes, filename=audio_filename)
        transcript = res.get("text", "").strip()
        language = res.get("language_code", language_code)
        if not transcript:
            return {**_blank, "error": res.get("error", "Could not understand speech. Please try again."), "language": language}

    if not transcript:
        return {**_blank, "error": "Empty query — please speak or type something."}

    # Stage 2 — Intent routing
    route = _router().route(transcript, context, language)
    intent = route["intent"]
    topic = route.get("topic")
    language = route.get("language", language)

    # Stage 3 — RAG + Explanation
    if intent == "diagram":
        data = _rag().retrieve(transcript, topic)
        response_text = (
            _explainer().generate(data, language)
            if data
            else _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
        )
    else:
        response_text = route.get("response", "")

    if not response_text:
        return {**_blank, "error": "Pipeline produced an empty response.", "transcript": transcript}

    # Stage 4 — TTS
    audio_out = _tts().synthesize_to_bytes(response_text, language)

    return {
        "transcript": transcript,
        "response_text": response_text,
        "audio_bytes": audio_out,
        "intent": intent,
        "topic": topic,
        "language": language,
        "error": None,
    }


def _render_msg(msg: dict) -> None:
    """Render a single chat bubble from a stored message dict."""
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["text"])
            if msg.get("input_audio"):
                mime = _AUDIO_MIMES.get(
                    Path(msg.get("audio_fn", "audio.wav")).suffix.lower(), "audio/wav"
                )
                with st.expander("Your recording", expanded=False):
                    st.audio(msg["input_audio"], format=mime)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            if msg.get("topic"):
                label = msg["topic"].replace("_", " ").title()
                st.caption(f"Explaining: **{label}**  ·  `{msg.get('language', '')}`")
            st.markdown(msg["text"])
            if msg.get("audio"):
                st.audio(msg["audio"], format="audio/wav")


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Asha — Learning Assistant",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Inject minimal CSS ────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* Give the assistant bubble a warm off-white background */
    [data-testid="stChatMessageContent"] {
        border-radius: 12px;
    }
    /* Tighten the sidebar logo area */
    .sidebar-logo { font-size: 2rem; text-align: center; padding: 0.5rem 0; }
    /* Status pills */
    .pill {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages: list[dict] = []
if "voice_key" not in st.session_state:
    # Incrementing this forces st.audio_input to reset (new key = new widget)
    st.session_state.voice_key: int = 0
if "pending_play_id" not in st.session_state:
    # ID of the assistant message whose audio should autoplay on next render
    st.session_state.pending_play_id: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">🤖</div>', unsafe_allow_html=True)
    st.markdown("### Asha")
    st.caption("NCERT Science Learning Assistant")
    st.divider()

    # Language
    lang_label: str = st.selectbox(
        "Respond in",
        list(LANGUAGES.keys()),
        index=0,
        help="Asha will explain diagrams in this language. When you speak, she auto-detects your language too.",
    )
    language_code: str = LANGUAGES[lang_label]

    st.divider()

    # ── Voice input ───────────────────────────────────────────────────────────
    st.markdown("#### Speak a Question")

    _rec_audio: bytes | None = None
    _rec_fn: str = "audio.wav"

    try:
        _recorded = st.audio_input(
            "Tap to record",
            key=f"mic_{st.session_state.voice_key}",
        )
        if _recorded is not None:
            _rec_audio = _recorded.read()
            _rec_fn = getattr(_recorded, "name", "audio.wav")
    except AttributeError:
        # Streamlit < 1.36 — fall back to file uploader
        st.caption("Upgrade Streamlit for mic support: `pip install -U streamlit`")
        _up = st.file_uploader(
            "Upload audio instead",
            type=["wav", "mp3", "ogg", "webm", "flac"],
            key=f"uploader_{st.session_state.voice_key}",
            label_visibility="collapsed",
        )
        if _up is not None:
            _rec_audio = _up.read()
            _rec_fn = _up.name

    _voice_clicked: bool = False
    if _rec_audio:
        _voice_clicked = st.button(
            "Send Voice Message",
            type="primary",
            use_container_width=True,
            key="voice_send",
        )

    st.divider()

    # ── Sample topics ─────────────────────────────────────────────────────────
    st.markdown("#### Quick Topics")
    _sample_query: str | None = None
    for _s in SAMPLES[language_code]:
        if st.button(_s, key=f"sq_{_s}", use_container_width=True):
            _sample_query = _s

    st.divider()

    # ── Settings ──────────────────────────────────────────────────────────────
    _mock: bool = st.toggle(
        "Mock Mode",
        value=not _BACKEND_OK,
        disabled=not _BACKEND_OK,
        help="Use demo data — no API keys needed. Disable to use real Sarvam AI + OpenAI.",
    )
    if not _BACKEND_OK:
        st.error(
            f"Backend unavailable — Mock Mode forced.\n\n"
            f"**Error:** `{_BACKEND_ERR[:120]}`\n\n"
            "Install missing packages and restart."
        )
    else:
        _s_ok = bool(os.getenv("SARVAM_API_KEY", "").strip())
        _o_ok = bool(os.getenv("OPENAI_API_KEY", "").strip())
        if not _mock:
            st.markdown(
                f"Sarvam AI: **{'connected' if _s_ok else 'key missing'}**  \n"
                f"OpenAI: **{'connected' if _o_ok else 'key missing'}**"
            )
            if not _s_ok or not _o_ok:
                st.warning("Add missing keys to `backend/.env`")

    st.divider()
    if st.button("Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_play_id = None
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Main chat area
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## Asha")
st.caption(
    f"Ask me to explain any NCERT science diagram and I will describe it — and read it aloud.  "
    f"Responding in **{lang_label}**."
    + ("  ·  *Mock Mode*" if _mock else "")
)
st.divider()

# Welcome message when conversation is empty
if not st.session_state.messages:
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(
            "Hello! I am **Asha**, your science learning assistant.\n\n"
            "I can describe scientific diagrams from your NCERT textbook in rich detail — "
            "and I will read the description aloud so you can follow along.\n\n"
            "Try asking about the **digestive system**, **photosynthesis**, **human eye**, "
            "**water cycle**, or **food chain**.  \n"
            "You can speak using the microphone in the sidebar, type below, "
            "or tap one of the quick topics."
        )

# ── Render conversation history ───────────────────────────────────────────────
for _msg in st.session_state.messages:
    _render_msg(_msg)

# ── Auto-play the latest assistant response ───────────────────────────────────
_pid = st.session_state.pending_play_id
if _pid:
    for _m in reversed(st.session_state.messages):
        if _m.get("id") == _pid and _m.get("audio"):
            _autoplay(_m["audio"])
            break
    st.session_state.pending_play_id = None

# ── Text input (fixed at bottom of screen) ───────────────────────────────────
_text_in = st.chat_input("Type your question, or use the mic in the sidebar…")


# ─────────────────────────────────────────────────────────────────────────────
# Resolve what the user submitted this turn
# ─────────────────────────────────────────────────────────────────────────────
_query: str | None = None
_proc_audio: bytes | None = None
_proc_fn: str = "audio.wav"
_is_voice: bool = False

if _text_in and _text_in.strip():
    _query = _text_in.strip()
elif _sample_query:
    _query = _sample_query
elif _voice_clicked and _rec_audio:
    _proc_audio = _rec_audio
    _proc_fn = _rec_fn
    _is_voice = True
    _query = "__voice__"  # sentinel


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline execution
# ─────────────────────────────────────────────────────────────────────────────
if _query:
    # --- User message --------------------------------------------------------
    _display_text = "🎤 Voice message…" if _is_voice else _query
    _user_id = str(uuid.uuid4())
    _user_msg: dict[str, Any] = {
        "id": _user_id,
        "role": "user",
        "text": _display_text,
        "input_audio": _proc_audio,
        "audio_fn": _proc_fn,
    }
    st.session_state.messages.append(_user_msg)

    # Render user bubble immediately (before the spinner)
    with st.chat_message("user"):
        st.markdown(_display_text)
        if _is_voice and _proc_audio:
            mime = _AUDIO_MIMES.get(Path(_proc_fn).suffix.lower(), "audio/wav")
            with st.expander("Your recording", expanded=False):
                st.audio(_proc_audio, format=mime)

    # --- Asha thinks ---------------------------------------------------------
    with st.chat_message("assistant", avatar="🤖"):
        _spinner_msg = "Listening and thinking…" if _is_voice else "Thinking…"
        with st.spinner(_spinner_msg):
            _ctx = _context_from_history(st.session_state.messages[:-1])
            _res = _run_pipeline(
                query="" if _is_voice else _query,
                language_code=language_code,
                context=_ctx,
                audio_bytes=_proc_audio,
                audio_filename=_proc_fn,
                mock=_mock,
            )

        # --- Handle error ----------------------------------------------------
        if _res.get("error"):
            err_msgs = {
                "en-IN": "I'm sorry, I ran into a problem",
                "hi-IN": "क्षमा करें, मुझे एक समस्या आई",
                "mr-IN": "माफ करा, मला एक अडचण आली",
            }
            prefix = err_msgs.get(language_code, err_msgs["en-IN"])
            st.error(f"{prefix}: {_res['error']}")
            # Remove the failed user message so chat stays clean
            st.session_state.messages.pop()

        # --- Success ---------------------------------------------------------
        else:
            # If it was a voice message, update the user bubble text to the
            # real transcript so the conversation reads naturally
            if _is_voice and _res.get("transcript"):
                st.session_state.messages[-1]["text"] = _res["transcript"]

            # Render topic label if this is a diagram explanation
            if _res.get("topic"):
                _label = _res["topic"].replace("_", " ").title()
                _lang = _res.get("language", language_code)
                st.caption(f"Explaining: **{_label}**  ·  `{_lang}`")

            # Render the spoken description
            st.markdown(_res["response_text"])

            # Show the audio player (user can replay manually)
            if _res["audio_bytes"]:
                st.audio(_res["audio_bytes"], format="audio/wav")

            # Persist the assistant message in session state
            _asst_id = str(uuid.uuid4())
            st.session_state.messages.append({
                "id": _asst_id,
                "role": "assistant",
                "text": _res["response_text"],
                "audio": _res["audio_bytes"],
                "intent": _res.get("intent"),
                "topic": _res.get("topic"),
                "language": _res.get("language", language_code),
            })

            # Queue autoplay for the next render cycle
            if _res["audio_bytes"]:
                st.session_state.pending_play_id = _asst_id

            # Reset the mic widget so the user can record again immediately
            if _is_voice:
                st.session_state.voice_key += 1

            # Rerun: resets all input widgets and triggers autoplay cleanly
            st.rerun()
