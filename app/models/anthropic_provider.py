from typing import List, Dict, AsyncGenerator, Optional
import logging
import asyncio
import anthropic
from app.config.settings import Settings

logger = logging.getLogger(__name__)

class AnthropicProvider:
    """
    Provider for Anthropic Claude models
    """
    def __init__(self):
        self.settings = Settings()
        self.client = anthropic.AsyncAnthropic(api_key=self.settings.ANTHROPIC_API_KEY)
        logger.info("Anthropic Claude provider initialized")
    
    async def generate(self, messages: List[Dict[str, str]], model_name: str) -> str:
        """Generate a response from an Anthropic Claude model"""
        try:
            # Format messages for Claude
            formatted_messages = self._format_messages(messages)
            
            # Generate response
            response = await self.client.messages.create(
                model=model_name,
                messages=formatted_messages,
                max_tokens=1024
            )
            
            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return f"Error with Anthropic API: {str(e)}"
    
    async def stream(self, messages: List[Dict[str, str]], model_name: str) -> AsyncGenerator[str, None]:
        """Stream a response from an Anthropic Claude model"""
        try:
            # Format messages for Claude
            formatted_messages = self._format_messages(messages)
            
            # Stream response
            with await self.client.messages.create(
                model=model_name,
                messages=formatted_messages,
                max_tokens=1024,
                stream=True
            ) as stream:
                async for chunk in stream:
                    if chunk.type == "content_block_delta" and chunk.delta.text:
                        yield chunk.delta.text
        except Exception as e:
            logger.error(f"Anthropic API streaming error: {str(e)}")
            yield f"Error with Anthropic API streaming: {str(e)}"
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Format messages to Anthropic Claude expected format"""
        # Claude expects messages in the format:
        # [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]
        
        formatted = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted.append({
                "role": role,
                "content": msg["content"]
            })
        return formatted 