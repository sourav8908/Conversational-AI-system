from typing import List, Dict, AsyncGenerator, Optional
import logging
import asyncio
import time
import re
import google.generativeai as genai
from google.generativeai.types import AsyncGenerateContentResponse
from app.config.settings import Settings

logger = logging.getLogger(__name__)

class GoogleProvider:
    """
    Provider for Google Gemini models
    """
    def __init__(self):
        self.settings = Settings()
        genai.configure(api_key=self.settings.GOOGLE_API_KEY)
        
        # Store rate limit information
        self.rate_limited_models = {}
        self.available_models = []
        
        # Check available models on initialization
        try:
            for model in genai.list_models():
                self.available_models.append(model.name)
                logger.info(f"Available Google model: {model.name}, supports: {', '.join(model.supported_generation_methods)}")
        except Exception as e:
            logger.error(f"Error listing Google models: {str(e)}")
            
        logger.info("Google Gemini provider initialized")
    
    async def generate(self, messages: List[Dict[str, str]], model_name: str) -> str:
        """Generate a response from a Google Gemini model"""
        try:
            logger.info(f"Generating response for {len(messages)} messages with model {model_name}")
            
            # Map our model name to the actual API model name
            api_model_name = self._get_api_model_name(model_name)
            logger.info(f"Using API model name: {api_model_name}")
            
            # Check if this model is rate limited
            if self._is_rate_limited(api_model_name):
                wait_time = self._get_rate_limit_wait_time(api_model_name)
                if wait_time > 10:  # If wait time is too long, try a different model
                    alt_model = self._get_alternative_model(api_model_name)
                    if alt_model:
                        logger.info(f"Model {api_model_name} is rate limited. Using alternative model: {alt_model}")
                        api_model_name = alt_model
                    else:
                        return f"Rate limit reached for {model_name}. Please try again in {wait_time} seconds or use a different model."
                else:
                    logger.info(f"Waiting {wait_time} seconds for rate limit to reset for {api_model_name}")
                    await asyncio.sleep(wait_time)
            
            # Configure the model
            model = genai.GenerativeModel(api_model_name)
            
            # Handle simple case with just one message
            if len(messages) == 1:
                user_message = messages[0].get("content", "") if isinstance(messages[0], dict) else ""
                try:
                    response = await model.generate_content_async(user_message)
                    return response.text
                except Exception as e:
                    error_msg = str(e)
                    # Handle rate limit errors
                    if "429" in error_msg:
                        retry_delay = self._extract_retry_delay(error_msg)
                        self._set_rate_limited(api_model_name, retry_delay)
                        
                        # Try to use an alternative model
                        alt_model = self._get_alternative_model(api_model_name)
                        if alt_model:
                            logger.info(f"Rate limited. Retrying with alternative model: {alt_model}")
                            model = genai.GenerativeModel(alt_model)
                            response = await model.generate_content_async(user_message)
                            return response.text
                        
                        return f"Rate limit reached for this model. Please try again in {retry_delay} seconds or try a different model."
                    raise
            
            # For chat history, use the chat format
            # Convert messages to proper format
            gemini_messages = []
            for msg in messages:
                if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                    continue
                
                content = msg.get("content", "")
                if msg["role"].lower() == "user":
                    gemini_messages.append({"role": "user", "parts": [content]})
                else:
                    gemini_messages.append({"role": "model", "parts": [content]})
            
            try:
                # Generate response using the chat API
                chat = model.start_chat(history=[])
                
                # Process each message in sequence to build chat history
                last_response = None
                for i, msg in enumerate(gemini_messages):
                    if msg["role"] == "user":
                        last_response = await chat.send_message_async(msg["parts"][0])
                
                # If we didn't get any response, handle it
                if not last_response:
                    if len(gemini_messages) > 0 and gemini_messages[-1]["role"] == "user":
                        last_response = await chat.send_message_async(gemini_messages[-1]["parts"][0])
                    else:
                        return "Error: Could not generate a response from the chat history."
                
                return last_response.text
            except Exception as e:
                error_msg = str(e)
                # Handle rate limit errors
                if "429" in error_msg:
                    retry_delay = self._extract_retry_delay(error_msg)
                    self._set_rate_limited(api_model_name, retry_delay)
                    return f"Rate limit reached for this model. Please try again in {retry_delay} seconds or try a different model."
                raise
            
        except Exception as e:
            logger.error(f"Google Gemini API error: {str(e)}")
            return f"Error with Google Gemini API: {str(e)}"
    
    async def stream(self, messages: List[Dict[str, str]], model_name: str) -> AsyncGenerator[str, None]:
        """Stream a response from a Google Gemini model"""
        try:
            logger.info(f"Streaming response for {len(messages)} messages with model {model_name}")
            
            # Log message format for debugging
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    logger.info(f"Message {i}: role={msg.get('role', 'unknown')}, content_length={len(msg.get('content', ''))}")
                else:
                    logger.info(f"Message {i}: type={type(msg)}")
            
            # Map our model name to the actual API model name
            api_model_name = self._get_api_model_name(model_name)
            logger.info(f"Using API model name: {api_model_name}")
            
            # Check if this model is rate limited
            if self._is_rate_limited(api_model_name):
                wait_time = self._get_rate_limit_wait_time(api_model_name)
                if wait_time > 10:  # If wait time is too long, try a different model
                    alt_model = self._get_alternative_model(api_model_name)
                    if alt_model:
                        logger.info(f"Model {api_model_name} is rate limited. Using alternative model: {alt_model}")
                        api_model_name = alt_model
                    else:
                        yield f"⚠️ Rate limit reached for {model_name}. Please try again in {wait_time} seconds or use a different model."
                        return
                else:
                    logger.info(f"Waiting {wait_time} seconds for rate limit to reset for {api_model_name}")
                    await asyncio.sleep(wait_time)
            
            # Configure the model
            model = genai.GenerativeModel(api_model_name)
            
            # For simple case with just one message
            if len(messages) == 1:
                try:
                    content = messages[0].get("content", "") if isinstance(messages[0], dict) else ""
                    if not content:
                        yield "Error: Empty user message."
                        return
                        
                    logger.info(f"Generating content for single message: {content[:50]}...")
                    response = await model.generate_content_async(
                        content,
                        stream=True
                    )
                    
                    async for chunk in response:
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text
                    return
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error in single message mode: {error_msg}")
                    
                    # Handle rate limit errors
                    if "429" in error_msg:
                        retry_delay = self._extract_retry_delay(error_msg)
                        self._set_rate_limited(api_model_name, retry_delay)
                        
                        # Try with an alternative model
                        alt_model = self._get_alternative_model(api_model_name)
                        if alt_model:
                            logger.info(f"Rate limited. Retrying with alternative model: {alt_model}")
                            yield f"⚠️ Rate limit reached. Switching to alternative model: {alt_model.split('/')[-1]}..."
                            
                            try:
                                alt_model_instance = genai.GenerativeModel(alt_model)
                                alt_response = await alt_model_instance.generate_content_async(
                                    content,
                                    stream=True
                                )
                                
                                async for chunk in alt_response:
                                    if hasattr(chunk, 'text') and chunk.text:
                                        yield chunk.text
                                return
                            except Exception as alt_error:
                                yield f"Error with alternative model: {str(alt_error)}"
                                return
                        
                        yield f"⚠️ Rate limit reached for this model. Please try again in {retry_delay} seconds or try a different model."
                        return
                    
                    yield f"Error processing single message: {error_msg}"
                    return
            
            # For chat history, use the chat format
            try:
                # Convert messages to proper format for Gemini
                gemini_messages = []
                for msg in messages:
                    if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                        continue
                    
                    content = msg.get("content", "")
                    if msg["role"].lower() == "user":
                        gemini_messages.append({"role": "user", "parts": [content]})
                    else:
                        gemini_messages.append({"role": "model", "parts": [content]})
                
                if not gemini_messages:
                    yield "Error: No valid messages found."
                    return
                
                # Start a new chat
                chat = model.start_chat(history=[])
                
                # Process all messages except the last one to build history
                for i in range(len(gemini_messages) - 1):
                    if gemini_messages[i]["role"] == "user":
                        await chat.send_message_async(gemini_messages[i]["parts"][0])
                
                # Stream the response to the last message
                last_msg = gemini_messages[-1]
                if last_msg["role"] != "user":
                    yield "Error: Last message must be from user."
                    return
                
                logger.info(f"Streaming response to: {last_msg['parts'][0][:50]}...")
                try:
                    response = await chat.send_message_async(
                        last_msg["parts"][0],
                        stream=True
                    )
                    
                    async for chunk in response:
                        if hasattr(chunk, 'text') and chunk.text:
                            yield chunk.text
                except Exception as e:
                    error_msg = str(e)
                    # Handle rate limit errors
                    if "429" in error_msg:
                        retry_delay = self._extract_retry_delay(error_msg)
                        self._set_rate_limited(api_model_name, retry_delay)
                        
                        # Try with an alternative model
                        alt_model = self._get_alternative_model(api_model_name)
                        if alt_model:
                            logger.info(f"Rate limited. Retrying with alternative model: {alt_model}")
                            yield f"⚠️ Rate limit reached. Switching to alternative model: {alt_model.split('/')[-1]}..."
                            
                            try:
                                # Create new chat with alternative model
                                alt_model_instance = genai.GenerativeModel(alt_model)
                                alt_chat = alt_model_instance.start_chat(history=[])
                                
                                # Send final message to get streaming response
                                alt_response = await alt_chat.send_message_async(
                                    last_msg["parts"][0],
                                    stream=True
                                )
                                
                                async for chunk in alt_response:
                                    if hasattr(chunk, 'text') and chunk.text:
                                        yield chunk.text
                                return
                            except Exception as alt_error:
                                yield f"Error with alternative model: {str(alt_error)}"
                                return
                        
                        yield f"⚠️ Rate limit reached for this model. Please try again in {retry_delay} seconds or try a different model."
                        return
                    
                    yield f"Error in chat mode: {error_msg}"
                         
            except Exception as e:
                logger.error(f"Error in chat mode: {str(e)}")
                yield f"Error in chat mode: {str(e)}"
                
        except Exception as e:
            logger.error(f"Google Gemini API streaming error: {str(e)}")
            yield f"Error with Google Gemini API streaming: {str(e)}"
    
    def _get_api_model_name(self, model_name: str) -> str:
        """Convert our model name to the actual API model name"""
        # Check if model name already includes 'models/' prefix
        if model_name.startswith("models/"):
            return model_name
            
        # Map known model names to their full API names with models/ prefix
        model_mapping = {
            "gemini-pro": "models/gemini-1.5-flash",  # Fallback to more reliable model
            "gemini-1.5-pro": "models/gemini-1.5-pro",
            "gemini-1.5-flash": "models/gemini-1.5-flash",
            "gemini-1.5-flash-latest": "models/gemini-1.5-flash-latest"
        }
        
        # Use the mapping or try to construct a valid model name with prefix
        mapped_name = model_mapping.get(model_name)
        if mapped_name:
            return mapped_name
            
        # If we have a list of available models, check if the model with prefix exists
        prefixed_name = f"models/{model_name}"
        if hasattr(self, 'available_models') and prefixed_name in self.available_models:
            return prefixed_name
            
        # As a last resort, return the prefixed name anyway
        return prefixed_name
    
    def _extract_retry_delay(self, error_message: str) -> int:
        """Extract retry delay from error message"""
        match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', error_message)
        if match:
            return int(match.group(1))
        return 60  # Default to 60 seconds if not found
    
    def _set_rate_limited(self, model_name: str, delay_seconds: int) -> None:
        """Mark a model as rate limited"""
        self.rate_limited_models[model_name] = {
            "until": time.time() + delay_seconds,
            "delay": delay_seconds
        }
        logger.info(f"Model {model_name} rate limited for {delay_seconds} seconds")
    
    def _is_rate_limited(self, model_name: str) -> bool:
        """Check if a model is currently rate limited"""
        if model_name in self.rate_limited_models:
            if time.time() < self.rate_limited_models[model_name]["until"]:
                return True
            else:
                # Rate limit has expired
                del self.rate_limited_models[model_name]
        return False
    
    def _get_rate_limit_wait_time(self, model_name: str) -> int:
        """Get the remaining wait time for a rate limited model"""
        if model_name in self.rate_limited_models:
            remaining = self.rate_limited_models[model_name]["until"] - time.time()
            return max(0, int(remaining))
        return 0
    
    def _get_alternative_model(self, model_name: str) -> Optional[str]:
        """Get an alternative model that's not rate limited"""
        # Define fallback order
        fallbacks = [
            "models/gemini-1.5-flash", 
            "models/gemini-1.5-flash-latest",
            "models/gemini-1.5-flash-8b",
            "models/gemini-1.5-flash-8b-latest"
        ]
        
        # Try each fallback model
        for fallback in fallbacks:
            if fallback != model_name and not self._is_rate_limited(fallback):
                # Ensure the fallback is actually available
                if fallback in self.available_models:
                    return fallback
        
        return None 