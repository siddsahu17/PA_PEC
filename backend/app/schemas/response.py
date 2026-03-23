from pydantic import BaseModel
from typing import Dict, Any, Optional

class ImageAnalysisResponse(BaseModel):
    structured: Dict[str, Any]
    explanation: str
    braille: str

class ChatVoiceResponse(BaseModel):
    transcription: str
    response: str
    audio_url: str # Path or URL to the generated audio
