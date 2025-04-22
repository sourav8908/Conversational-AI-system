from typing import List, Dict, AsyncGenerator, Optional
import logging
import asyncio
import json
from openai import AsyncOpenAI
from app.config.settings import Settings

logger = logging.getLogger(__name__)

class OpenAIProvider:
    """
    Provider for OpenAI models (GPT-3.5, GPT-4)
    """
    def __init__(self):
        self.settings = Settings()
        # Only initialize client if API key is available
        self.client = None
        if self.settings.OPENAI_API_KEY:
            self.client = AsyncOpenAI(api_key=self.settings.OPENAI_API_KEY)
            logger.info("OpenAI provider initialized")
        else:
            logger.warning("OpenAI API key not configured, provider will return error messages")
    
    async def generate(self, messages: List[Dict[str, str]], model_name: str) -> str:
        """Generate a response from an OpenAI model"""
        if not self.settings.OPENAI_API_KEY:
            return "Error: OpenAI API key not configured. Please set your OPENAI_API_KEY."
            
        try:
            # Convert messages to OpenAI format if needed
            formatted_messages = self._format_messages(messages)
            
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return f"Error with OpenAI API: {str(e)}"
    
    async def stream(self, messages: List[Dict[str, str]], model_name: str) -> AsyncGenerator[str, None]:
        """Stream a response from an OpenAI model"""
        if not self.settings.OPENAI_API_KEY:
            yield "Error: OpenAI API key not configured. Please set your OPENAI_API_KEY."
            return
            
        try:
            # Convert messages to OpenAI format if needed
            formatted_messages = self._format_messages(messages)
            
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=formatted_messages,
                stream=True
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API streaming error: {str(e)}")
            yield f"Error with OpenAI API streaming: {str(e)}"
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages to OpenAI expected format"""
        # OpenAI expects messages in the format: [{"role": "user", "content": "Hello"}, ...]
        # Our messages should already be in this format, but we can add validation here
        formatted = []
        for msg in messages:
            if "role" in msg and "content" in msg:
                formatted.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        return formatted 