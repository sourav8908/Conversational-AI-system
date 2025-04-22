from fastapi import FastAPI, HTTPException, WebSocket, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import asyncio
import json
import uuid
from app.models.llm_manager import LLMManager
from app.config.settings import Settings

settings = Settings()
app = FastAPI(title="MCP - Model Control Plane")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models for request/response
class ChatMessage(BaseModel):
    role: str
    content: str
    
    def dict(self):
        return {"role": self.role, "content": self.content}

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = False

class ChatResponse(BaseModel):
    message: ChatMessage
    conversation_id: str

# Store active conversations
conversations: Dict[str, List[ChatMessage]] = {}

# Get the LLM manager instance
llm_manager = LLMManager()

@app.get("/")
async def root():
    return {"message": "Conversational AI MCP Server is running"}

@app.get("/models")
async def get_available_models():
    return {
        "models": llm_manager.get_available_models(),
        "current_model": llm_manager.current_model
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    conversation_id = str(uuid.uuid4())
    
    # Store conversation history
    conversations[conversation_id] = request.messages
    
    # Convert Pydantic models to dictionaries for the LLM manager
    message_dicts = [msg.dict() for msg in request.messages]
    
    # Process with LLM
    response = await llm_manager.generate_response(
        message_dicts, 
        model=request.model
    )
    
    # Add response to conversation history
    ai_message = ChatMessage(role="assistant", content=response)
    conversations[conversation_id].append(ai_message)
    
    return ChatResponse(
        message=ai_message,
        conversation_id=conversation_id
    )

@app.websocket("/chat/stream")
async def chat_stream(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            request_data = json.loads(data)
            
            # Process messages into proper format
            raw_messages = request_data.get("messages", [])
            messages = [ChatMessage(**msg) for msg in raw_messages]
            
            # Convert Pydantic models to plain dictionaries
            message_dicts = [{"role": msg.role, "content": msg.content} for msg in messages]
            
            model = request_data.get("model")
            conversation_id = request_data.get("conversation_id", str(uuid.uuid4()))
            
            # Store or update conversation history
            if conversation_id not in conversations:
                conversations[conversation_id] = []
            conversations[conversation_id].extend(messages)
            
            # Stream response
            async for chunk in llm_manager.generate_stream(
                message_dicts,  # Use the dictionary list instead of ChatMessage objects
                model=model
            ):
                await websocket.send_text(json.dumps({
                    "chunk": chunk,
                    "conversation_id": conversation_id,
                    "done": False
                }))
            
            # Send completion message
            await websocket.send_text(json.dumps({
                "chunk": "",
                "conversation_id": conversation_id,
                "done": True
            }))
                
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "error": str(e),
                "done": True
            }))
        except:
            # In case the connection is already closed
            pass
    
    finally:
        try:
            await websocket.close()
        except:
            # In case the connection is already closed
            pass

@app.post("/switch_model")
async def switch_model(request: Dict[str, str]):
    try:
        model = request.get("model")
        if not model:
            raise HTTPException(status_code=400, detail="Model name is required")
        
        result = llm_manager.switch_model(model)
        if not result:
            raise HTTPException(status_code=400, detail=f"Failed to switch to model: {model}")
        
        return {"message": f"Successfully switched to model: {model}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 