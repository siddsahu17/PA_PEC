from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # Application configuration
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    ENVIRONMENT: str = Field(default="development")
    
    # OpenAI config
    OPENAI_API_KEY: str = Field(default="")
    
    # Whisper Config
    WHISPER_MODEL: str = Field(default="base")
    
    # Paths Config
    UPLOAD_DIR: str = Field(default="app/data/uploads")
    TEMP_DIR: str = Field(default="app/data/temp")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
