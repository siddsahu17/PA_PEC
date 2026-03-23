from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
import logging

from app.api.deps import get_pipeline
from app.core.pipeline import AssistantPipeline
from app.utils.validators import validate_audio_type
from app.utils.file_utils import save_upload_file, cleanup_file
from app.utils.audio_utils import convert_to_wav
from app.schemas.response import ChatVoiceResponse

logger = logging.getLogger("assistant_backend.api.chat")
router = APIRouter()

@router.post("/voice", response_model=ChatVoiceResponse)
async def chat_voice(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
    pipeline: AssistantPipeline = Depends(get_pipeline)
):
    logger.info(f"Received voice chat request for session: {session_id}")
    validate_audio_type(audio.content_type)
    
    file_path = ""
    wav_path = ""
    try:
        # Save temp file
        file_path = await save_upload_file(audio)
        
        # Convert to WAV for safe whisper processing
        wav_path = file_path + ".wav"
        convert_to_wav(file_path, wav_path)
        
        # Run pipeline
        result = await pipeline.process_voice(wav_path, session_id)
        
        return ChatVoiceResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in /chat/voice: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if file_path:
            cleanup_file(file_path)
        if wav_path:
            cleanup_file(wav_path)
