from pydantic_settings import BaseSettings
from typing import Dict, Optional, List

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    
    # Model Configuration
    DEFAULT_MODEL: str = "gemini-1.5-flash"  # Using flash model with higher rate limits
    
    # Available Models
    AVAILABLE_MODELS: Dict[str, Dict[str, str]] = {
        # OpenAI Models
        "gpt-3.5-turbo": {"provider": "openai", "name": "gpt-3.5-turbo"},
        "gpt-4": {"provider": "openai", "name": "gpt-4"},
        
        # Google Models - The provider will handle the proper API model naming
        "gemini-1.5-flash": {"provider": "google", "name": "gemini-1.5-flash"},
        "gemini-1.5-flash-latest": {"provider": "google", "name": "gemini-1.5-flash-latest"},
        "gemini-pro": {"provider": "google", "name": "gemini-pro"},
        "gemini-1.5-pro": {"provider": "google", "name": "gemini-1.5-pro"},
        
        # Anthropic Models
        "claude-3-opus": {"provider": "anthropic", "name": "claude-3-opus"},
        "claude-3-sonnet": {"provider": "anthropic", "name": "claude-3-sonnet"},
        "claude-3-haiku": {"provider": "anthropic", "name": "claude-3-haiku"}
    }
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8" 