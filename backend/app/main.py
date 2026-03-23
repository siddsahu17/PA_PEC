from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.config.logging import logger
from app.api.routes import image, chat, health
import os

def create_app() -> FastAPI:
    logger.info(f"Starting Assistant Backend in {settings.ENVIRONMENT} mode.")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.TEMP_DIR, exist_ok=True)
    
    app = FastAPI(
        title="Conversational Learning Assistant API",
        description="Backend API for an AI-powered conversational assistant for visually impaired students.",
        version="1.0.0"
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(image.router, prefix="/image", tags=["image"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])

    return app

app = create_app()
