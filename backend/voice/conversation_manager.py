import logging

logger = logging.getLogger(__name__)

class ConversationManager:
    def __init__(self, max_history=10):
        self.max_history = max_history
        self.system_prompt = {
            "role": "system", 
            "content": "You are a smart, concise, voice assistant like Siri or Alexa. Keep responses short, clear, and conversational. Never use formatting like bolding or code blocks since this will be read aloud."
        }
        self.history = []

    def add_user_message(self, text: str):
        self.history.append({"role": "user", "content": text})
        self._trim_history()

    def add_assistant_message(self, text: str):
        self.history.append({"role": "assistant", "content": text})
        self._trim_history()

    def get_context(self):
        """Returns the full conversation context including the system prompt."""
        return [self.system_prompt] + self.history

    def _trim_history(self):
        """Keep only the last N interactions (N users + N assistants)."""
        # Multiply by 2 because 1 interaction = user + assistant
        limit = self.max_history * 2
        if len(self.history) > limit:
            self.history = self.history[-limit:]
            
    def clear(self):
        self.history = []
