from typing import List, Dict, Any

class ConversationMemory:
    """
    A simple in-memory storage for current conversations.
    In a real-world scenario, this should be a DB like Redis or Postgres.
    """
    def __init__(self):
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}

    def get_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, role: str, content: str):
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": role, "content": content})

    def clear(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

# Singleton instance
memory = ConversationMemory()
