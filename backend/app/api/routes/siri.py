import base64
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from voice.voice_assistant import VoiceAssistant

logger = logging.getLogger("assistant_backend.api.siri")
router = APIRouter()

_assistant = VoiceAssistant()

_NOT_FOUND = {
    "en-IN": (
        "Sorry, I don't have data for that topic yet. "
        "I can explain: digestive system, photosynthesis, human eye, "
        "water cycle, and food chain."
    ),
    "hi-IN": (
        "क्षमा करें, इस विषय पर मेरे पास अभी जानकारी नहीं है। "
        "मैं इनके बारे में बता सकता हूँ: पाचन तंत्र, प्रकाश संश्लेषण, "
        "मानव नेत्र, जल चक्र और खाद्य श्रृंखला।"
    ),
    "mr-IN": (
        "माफ करा, या विषयावर माझ्याकडे अजून माहिती नाही. "
        "मी यांबद्दल सांगू शकतो: पाचन संस्था, प्रकाश संश्लेषण, "
        "मानवी डोळा, जलचक्र आणि अन्नसाखळी."
    ),
}


@router.post("/siri-chat")
async def siri_chat(audio: UploadFile = File(...)):
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file received.")

    filename = audio.filename or "audio.webm"
    logger.info("siri-chat: %d bytes  filename=%s", len(audio_bytes), filename)

    # ── 1. Speech-to-Text ────────────────────────────────────────────
    stt_res    = _assistant.stt.transcribe(audio_bytes, filename=filename)
    transcript = stt_res.get("text", "").strip()
    language   = stt_res.get("language_code", "en-IN")

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail=stt_res.get("error", "Could not transcribe audio — please speak clearly."),
        )

    logger.info("transcript [%s]: %s", language, transcript)

    # ── 2. Intent routing ─────────────────────────────────────────────
    context  = _assistant.convo.get_context()
    route    = _assistant.router.route(transcript, context, language)
    intent   = route["intent"]
    language = route.get("language", language)

    # ── 3. Generate response text + collect diagram data ─────────────
    topic_data: dict | None = None

    if intent == "diagram":
        topic_data    = _assistant.rag.retrieve(transcript, route.get("topic"))
        if topic_data:
            response_text = _assistant.explainer.generate(topic_data, language)
        else:
            response_text = _NOT_FOUND.get(language, _NOT_FOUND["en-IN"])
    else:
        response_text = route.get("response", "")

    # ── 4. Update conversation memory ─────────────────────────────────
    _assistant.convo.add_user_message(transcript)
    _assistant.convo.add_assistant_message(response_text)
    logger.info("response [%s, %s]: %s", intent, language, response_text[:80])

    # ── 5. Text-to-Speech via Sarvam AI ──────────────────────────────
    audio_b64 = ""
    try:
        tts_bytes = _assistant.tts.synthesize_to_bytes(response_text, language)
        if tts_bytes:
            audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")
    except Exception as exc:
        logger.warning("TTS synthesis failed (audio will be silent): %s", exc)

    return {
        "success":       True,
        "transcription": transcript,
        "response":      response_text,
        "language":      language,
        "audio_base64":  audio_b64,
        "topic_data":    topic_data,   # full RAG dict or null
    }
