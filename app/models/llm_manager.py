from typing import List, Dict, Optional, AsyncGenerator, Any
import asyncio
import logging
from app.config.settings import Settings
from app.models.openai_provider import OpenAIProvider
from app.models.google_provider import GoogleProvider
from app.models.anthropic_provider import AnthropicProvider

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMManager:
    """
    Manager class for handling different LLM providers
    """
    def __init__(self):
        self.settings = Settings()
        
        # Initialize providers
        self.providers = {
            "openai": OpenAIProvider(),
            "google": GoogleProvider(),
            "anthropic": AnthropicProvider()
        }
        
        # Set current model
        self.current_model = self.settings.DEFAULT_MODEL
        self._current_provider = self._get_provider_for_model(self.current_model)
        
        logger.info(f"LLM Manager initialized with default model: {self.current_model}")
    
    def _get_provider_for_model(self, model_name: str) -> str:
        """Get the provider name for a given model"""
        if model_name not in self.settings.AVAILABLE_MODELS:
            logger.warning(f"Unknown model: {model_name}, falling back to default")
            model_name = self.settings.DEFAULT_MODEL
            
        return self.settings.AVAILABLE_MODELS[model_name]["provider"]
    
    def get_available_models(self) -> List[str]:
        """Return list of available models"""
        return list(self.settings.AVAILABLE_MODELS.keys())
    
    def switch_model(self, model_name: str) -> bool:
        """Switch to a different model"""
        if model_name not in self.settings.AVAILABLE_MODELS:
            logger.error(f"Cannot switch to unknown model: {model_name}")
            return False
        
        self.current_model = model_name
        self._current_provider = self._get_provider_for_model(model_name)
        logger.info(f"Switched to model: {model_name} (Provider: {self._current_provider})")
        return True
    
    async def generate_response(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
        """Generate a response from the current model"""
        # Use specified model or default to current model
        model_to_use = model if model else self.current_model
        provider_name = self._get_provider_for_model(model_to_use)
        
        try:
            provider = self.providers[provider_name]
            response = await provider.generate(messages, model_to_use)
            return response
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error: Failed to generate response: {str(e)}"
    
    async def generate_stream(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream a response from the current model"""
        # Use specified model or default to current model
        model_to_use = model if model else self.current_model
        provider_name = self._get_provider_for_model(model_to_use)
        
        try:
            provider = self.providers[provider_name]
            async for chunk in provider.stream(messages, model_to_use):
                yield chunk
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            yield f"Error: Failed to stream response: {str(e)}" 