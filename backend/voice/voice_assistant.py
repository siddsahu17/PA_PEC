import logging
from .mic_listener import MicListener
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from .conversation_manager import ConversationManager
from .intent_router import IntentRouter

logger = logging.getLogger(__name__)

class VoiceAssistant:
    def __init__(self):
        self.mic = MicListener()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.convo = ConversationManager()
        self.router = IntentRouter()

    def run_step_by_step(self):
        """
        Executes a single conversational loop turn as a generator, 
        yielding state updates so the UI can stream intermediate responses.
        """
        yield {"status": "listening", "message": "Listening for speech..."}
        
        mic_res = self.mic.listen_blocking(timeout=5, phrase_time_limit=20)
        
        if mic_res["error"] == "timeout":
            yield {"status": "idle", "message": "No speech detected. Waiting..."}
            return
        elif mic_res["error"]:
            yield {"status": "error", "message": f"Microphone Hardware Error: {mic_res['error']}. Check if your mic is connected!"}
            return
            
        audio = mic_res["audio"]
        
        yield {"status": "transcribing", "message": "Transcribing speech to text..."}
        stt_result = self.stt.transcribe(audio)
        user_text = stt_result.get("text", "")
        
        if not user_text:
            yield {"status": "error", "message": "Audio captured, but couldn't transcribe any words."}
            return

        # Add to Memory
        self.convo.add_user_message(user_text)
        yield {"status": "user_spoken", "text": user_text, "message": "Thinking of a response..."}

        # Route Intent & Generate Response
        logger.info(f"Routing intent for: {user_text}")
        context = self.convo.get_context()
        route_result = self.router.route(user_text, context)
        assistant_text = route_result["response"]
        intent = route_result["intent"]

        # Add Assistant Response to Memory
        self.convo.add_assistant_message(assistant_text)
        yield {"status": "assistant_responded", "text": assistant_text, "intent": intent, "message": "Generating Voice..."}

        # Speak Response
        logger.info("Speaking response...")
        self.tts.speak(assistant_text)
        
        yield {"status": "done", "message": "Turn complete"}
