from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    # Assuming audio files are uploaded via multipart/form-data rather than base64 in JSON 
    # but we can provide a schema for JSON just in case.
