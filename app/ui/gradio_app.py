import gradio as gr
import requests
import json
import asyncio
import websockets
import logging
import time
from typing import List, Dict, Any, Tuple, AsyncGenerator
from app.config.settings import Settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = Settings()

class ChatUI:
    def __init__(self, api_url="http://localhost:8000"):
        self.api_url = api_url
        self.websocket_url = f"ws://localhost:8000/chat/stream"
        self.models = self._fetch_available_models()
        self.current_model = settings.DEFAULT_MODEL
        self.conversation_id = None
        
    def _fetch_available_models(self) -> List[str]:
        """Fetch available models from the MCP server"""
        try:
            response = requests.get(f"{self.api_url}/models")
            data = response.json()
            self.current_model = data.get("current_model", settings.DEFAULT_MODEL)
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to fetch models: {str(e)}")
            return list(settings.AVAILABLE_MODELS.keys())
    
    def switch_model(self, model_name: str) -> str:
        """Switch the active model"""
        try:
            response = requests.post(
                f"{self.api_url}/switch_model",
                json={"model": model_name}
            )
            if response.status_code == 200:
                self.current_model = model_name
                return f"Switched to model: {model_name}"
            else:
                return f"Failed to switch model: {response.json().get('detail', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Error switching model: {str(e)}")
            return f"Error: {str(e)}"
    
    async def chat(self, message: str, history: List[Tuple[str, str]], stream: bool = True) -> Tuple[str, List[Tuple[str, str]]]:
        """Chat with the AI using streaming or standard responses"""
        # Format messages from chat history
        messages = []
        for user_msg, ai_msg in history:
            messages.append({"role": "user", "content": user_msg})
            if ai_msg:  # Some messages might not have a response yet
                messages.append({"role": "assistant", "content": ai_msg})
        
        # Add the current message
        messages.append({"role": "user", "content": message})
        
        if stream:
            return await self._stream_chat(messages)
        else:
            return await self._standard_chat(messages)
    
    async def _standard_chat(self, messages: List[Dict[str, str]]) -> str:
        """Send a standard (non-streaming) chat request"""
        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json={
                    "messages": messages,
                    "model": self.current_model,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.conversation_id = data.get("conversation_id")
                return data["message"]["content"]
            else:
                return f"Error: {response.json().get('detail', 'Unknown error')}"
        except Exception as e:
            logger.error(f"Error in standard chat: {str(e)}")
            return f"Error: {str(e)}"
    
    async def _stream_chat(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Send a streaming chat request via WebSocket"""
        response_text = ""
        try:
            # Prepare request data
            request_data = {
                "messages": messages,
                "model": self.current_model,
                "conversation_id": self.conversation_id
            }
            
            # Connect to websocket
            async with websockets.connect(self.websocket_url) as websocket:
                # Send the initial message
                await websocket.send(json.dumps(request_data))
                
                # Process streaming response
                while True:
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if "error" in data:
                        yield f"Error: {data['error']}"
                        break
                    
                    if data.get("done", False):
                        break
                    
                    chunk = data.get("chunk", "")
                    response_text += chunk
                    
                    # For Gradio streaming, we need to yield updates
                    yield response_text
                
            # Update conversation ID if provided
            if "conversation_id" in data:
                self.conversation_id = data["conversation_id"]
                
            # Final yield for completeness
            if response_text:
                yield response_text
                
        except Exception as e:
            logger.error(f"Error in streaming chat: {str(e)}")
            yield f"Error: {str(e)}"

def create_chat_ui():
    """Create and launch the Gradio UI"""
    chat_ui = ChatUI()
    
    with gr.Blocks(title="Conversational AI") as demo:
        gr.Markdown("# 🤖 Conversational AI Chat")
        
        with gr.Row():
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(height=600, show_copy_button=True)
                
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Type your message here...",
                        show_label=False,
                        container=False,
                        scale=9
                    )
                    submit_btn = gr.Button("Send", scale=1)
                
                with gr.Row():
                    clear_btn = gr.Button("Clear Chat")
                    
            with gr.Column(scale=1):
                gr.Markdown("## Model Settings")
                model_dropdown = gr.Dropdown(
                    choices=chat_ui.models,
                    value=chat_ui.current_model,
                    label="Select Model"
                )
                streaming_checkbox = gr.Checkbox(
                    label="Enable Streaming",
                    value=True
                )
                
                model_info = gr.Markdown(f"**Current Model:** {chat_ui.current_model}")
                
                switch_btn = gr.Button("Switch Model")

        # Event handlers
        async def user_submit(message, history, model, streaming):
            if not message.strip():
                yield "", history
                return
                
            chat_ui.current_model = model
            history.append((message, ""))
            
            if streaming:
                # For streaming mode, we'll build the response incrementally
                history[-1] = (message, "")
                partial_resp = ""
                
                async for partial_resp in chat_ui._stream_chat(
                    [{"role": "user" if i % 2 == 0 else "assistant", "content": m} 
                     for i, m in enumerate([msg for pair in history[:-1] for msg in pair] + [message])]
                ):
                    history[-1] = (message, partial_resp)
                    yield "", history
            else:
                # For non-streaming, we'll get the complete response
                response = await chat_ui._standard_chat(
                    [{"role": "user" if i % 2 == 0 else "assistant", "content": m} 
                     for i, m in enumerate([msg for pair in history[:-1] for msg in pair] + [message])]
                )
                history[-1] = (message, response)
                yield "", history
                
        def clear_chat():
            chat_ui.conversation_id = None
            return [], None
            
        def switch_model_handler(model):
            result = chat_ui.switch_model(model)
            return f"**Current Model:** {model}\n\n{result}"
            
        # Connect UI elements to handlers
        submit_btn.click(
            user_submit, 
            inputs=[msg, chatbot, model_dropdown, streaming_checkbox], 
            outputs=[msg, chatbot]
        )
        
        msg.submit(
            user_submit, 
            inputs=[msg, chatbot, model_dropdown, streaming_checkbox], 
            outputs=[msg, chatbot]
        )
        
        clear_btn.click(
            clear_chat, 
            outputs=[chatbot, msg]
        )
        
        switch_btn.click(
            switch_model_handler, 
            inputs=[model_dropdown], 
            outputs=[model_info]
        )
        
    return demo
    
def launch_ui():
    """Launch the Gradio UI"""
    demo = create_chat_ui()
    demo.launch(share=True)
    
if __name__ == "__main__":
    launch_ui() 