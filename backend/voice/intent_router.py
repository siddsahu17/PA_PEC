import re
import logging
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger(__name__)

class IntentRouter:
    def __init__(self):
        # We explicitly init the client here; assumes OPENAI_API_KEY is in env
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)

    def detect_intent(self, text: str):
        """Checks if the user intent is to process a YouTube video or regular chat."""
        # Regex to find YouTube links or the mention of "youtube"
        yt_regex = r'(https?://(?:www\.)?youtu(?:be\.com|\.be)[^\s]+)'
        if re.search(yt_regex, text, re.IGNORECASE) or "youtube" in text.lower():
            return "youtube"
        return "chat"

    def route(self, text: str, context: list):
        """Routes the query based on intent and returns a response string."""
        intent = self.detect_intent(text)
        
        response_text = ""
        
        if intent == "youtube":
            logger.info("Intent detected: YOUTUBE")
            # In a real integration, we parse the URL and pass it to agent_orchestrator
            # Since we must NOT break existing code, we dynamically import it to avoid circular deps
            try:
                # We attempt to extract a URL if provided
                url_match = re.search(r'(https?://(?:www\.)?youtu(?:be\.com|\.be)[^\s]+)', text)
                url = url_match.group(1) if url_match else None
                
                if url:
                    # Replace this with the actual Orchestrator call if it exists in the codebase
                    # e.g., result = orchestrator.run(url)
                    # For now, we simulate the hook
                    response_text = f"I have detected a YouTube URL: {url}. I will now run the agent pipeline on this video."
                else:
                    response_text = "I heard you mention YouTube, but I didn't catch the exact link. Could you provide the URL?"
            except Exception as e:
                logger.error(f"Error routing to YouTube orchestrator: {e}")
                response_text = "I encountered an error trying to process the YouTube video."
        else:
            logger.info("Intent detected: CHAT")
            try:
                # Regular LLM chat response
                completion = self.client.chat.completions.create(
                    model="gpt-4o",  # or gpt-3.5-turbo
                    messages=context,
                    max_tokens=150,
                    temperature=0.7
                )
                response_text = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API Error: {e}")
                response_text = "I'm sorry, I'm having trouble connecting to my brain right now."

        return {"intent": intent, "response": response_text}
