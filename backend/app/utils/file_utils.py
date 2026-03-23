import os
import shutil
import uuid
from fastapi import UploadFile
from app.config.settings import settings

async def save_upload_file(upload_file: UploadFile, extension: str = None) -> str:
    """Saves an UploadFile to the temporary directory and returns the path."""
    if not extension:
        # Try to infer extension
        filename = upload_file.filename
        if filename and "." in filename:
            extension = filename.split(".")[-1]
        else:
            extension = "tmp"
            
    file_name = f"{uuid.uuid4()}.{extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
        
    return file_path

def cleanup_file(file_path: str):
    """Deletes a file if it exists."""
    if os.path.exists(file_path):
        os.remove(file_path)
