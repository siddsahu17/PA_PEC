from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import JSONResponse
import logging

from app.api.deps import get_pipeline
from app.core.pipeline import AssistantPipeline
from app.utils.validators import validate_image_type
from app.utils.file_utils import save_upload_file, cleanup_file
from app.schemas.response import ImageAnalysisResponse

logger = logging.getLogger("assistant_backend.api.image")
router = APIRouter()

@router.post("/analyze", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    pipeline: AssistantPipeline = Depends(get_pipeline)
):
    logger.info(f"Received image layout request: {file.filename}")
    validate_image_type(file.content_type)
    
    file_path = ""
    try:
        # Save temp file
        file_path = await save_upload_file(file)
        
        # Run pipeline
        result = await pipeline.process_image(file_path)
        
        return ImageAnalysisResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in /image/analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if file_path:
            cleanup_file(file_path)
