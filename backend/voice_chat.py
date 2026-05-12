"""
voice_chat.py — Pure Voice-to-Voice Assistant (Siri-Style)

This script provides a continuous, hands-free conversational loop.
It actively listens, transcribes, processes the intent, and speaks the response.

Run:
    python voice_chat.py
"""

import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pygame
import speech_recognition as sr
from dotenv import load_dotenv

# Ensure the backend directory is in the path for imports
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

load_dotenv(_BACKEND_DIR / ".env")

# Fail fast on missing keys
missing = [k for k in ("SARVAM_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
if missing:
    print(f"\nERROR: Missing API key(s): {', '.join(missing)}")
    print(f"Add them to {_BACKEND_DIR / '.env'} and restart.\n")
    sys.exit(1)

from voice.speech_to_text import SpeechToText
from voice.intent_router import IntentRouter
from voice.diagram_rag_agent import DiagramRAGAgent
from voice.explanation_agent import ExplanationAgent
from voice.text_to_speech import TextToSpeech

_MIXER_READY = False

def init_pygame():
    global _MIXER_READY
    try:
        pygame.mixer.init(frequency=22050)
        _MIXER_READY = True
    except Exception as e:
        print(f"WARNING: pygame not available — audio disabled. ({e})")

def play_wav(wav_bytes: bytes) -> None:
    if not _MIXER_READY or not wav_bytes:
        return
    tmp = None
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
        print(f"Playback error: {e}")
    finally:
        if tmp:
            try:
                os.remove(tmp)
            except Exception:
                pass

def speak(tts: TextToSpeech, text: str, lang: str) -> None:
    play_wav(tts.synthesize_to_bytes(text, lang))

def pipeline_worker(user_text: str, language: str, context: list, result: dict, done: threading.Event):
    try:
        route = IntentRouter().route(user_text, context, language)
        intent = route["intent"]
        lang_out = route.get("language", language)

        if intent == "diagram":
            data = DiagramRAGAgent().retrieve(user_text, route.get("topic"))
            if data:
                response = ExplanationAgent().generate(data, lang_out)
            else:
                response = "Sorry, I don't have data for that topic yet."
        else:
            response = route.get("response", "")

        audio = TextToSpeech().synthesize_to_bytes(response, lang_out)
        result.update({"success": True, "response": response, "language": lang_out, "intent": intent, "audio": audio})
    except Exception as e:
        result.update({"success": False, "error": str(e)})
    finally:
        done.set()

def main():
    init_pygame()

    print("\n" + "=" * 60)
    print("  Asha — Pure Voice Assistant (Siri-Style)")
    print("=" * 60)
    print("  Speak naturally. The assistant will detect your language.")
    print("  Say 'goodbye', 'exit', or 'stop' to end the conversation.")
    print("=" * 60 + "\n")

    stt = SpeechToText()
    tts = TextToSpeech()

    recognizer = sr.Recognizer()
    recognizer.pause_threshold = 1.0
    recognizer.energy_threshold = 300

    language = "en-IN"
    context = []
    
    print("Calibrating microphone (1.5s) — stay quiet…")
    try:
        with sr.Microphone() as mic:
            recognizer.adjust_for_ambient_noise(mic, duration=1.5)
        print("Ready to chat!\n")
    except Exception as e:
        print(f"WARNING: Calibration failed: {e}\n")

    speak(tts, "Hello! I am your voice assistant. How can I help you today?", language)

    exit_words = {"bye", "goodbye", "exit", "quit", "stop", "अलविदा", "बंद", "निरोप", "थांबा"}

    with sr.Microphone() as mic:
        while True:
            print("─" * 50)
            print("🎙️  [Listening…]")
            try:
                audio = recognizer.listen(mic, timeout=None, phrase_time_limit=25.0)
            except Exception as e:
                print(f"⚠️  [Mic error: {e}]")
                continue

            print("⚙️  [Transcribing…]")
            wav = audio.get_wav_data()
            res = stt.transcribe(wav, filename="audio.wav")
            text = res.get("text", "").strip()
            detected_lang = res.get("language_code", language)

            if not text:
                print("🤷  [No speech detected]")
                continue

            language = detected_lang
            print(f"👤  You: {text}")

            lower_text = text.lower()
            if any(w in lower_text for w in exit_words):
                print("\n👋  [Exiting]\n")
                speak(tts, "Goodbye! Have a great day!", language)
                break

            # Run thinking pipeline in the background
            print("🤖  [Thinking…]")
            result = {"success": False, "audio": b"", "response": "", "language": language, "intent": "chat"}
            done = threading.Event()
            threading.Thread(
                target=pipeline_worker,
                args=(text, language, list(context), result, done),
                daemon=True,
            ).start()

            # Wait for AI to finish generating response
            done.wait()

            if not result["success"]:
                print(f"❌  [Error: {result.get('error', 'unknown')}]")
                speak(tts, "I had trouble processing that.", language)
            else:
                language = result["language"]
                response_text = result["response"]
                print(f"🗣️  Assistant: {response_text}")
                
                # Update context history
                context.extend([{"role": "user", "content": text}, {"role": "assistant", "content": response_text}])
                context = context[-20:]
                
                # Speak out loud
                play_wav(result["audio"])

if __name__ == "__main__":
    main()
