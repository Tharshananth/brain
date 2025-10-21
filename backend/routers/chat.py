"""
Chat API endpoints
Handles chat conversations with RAG system
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncIterator
import uuid
from datetime import datetime
import logging

from llm.factory import get_llm_factory
from llm.base import Message, LLMResponse
from vector_db.retriever import DocumentRetriever
from utils.validators import ChatMessageValidator
from config import get_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory conversation storage (replace with database in production)
conversations = {}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[ChatMessage]] = []
    session_id: Optional[str] = None
    provider: Optional[str] = None  # Allow provider selection

class Source(BaseModel):
    title: str
    url: str
    content: str

class ChatResponse(BaseModel):
    response: str
    sources: List[Source]
    session_id: str
    success: bool
    provider_used: str
    tokens_used: Optional[int] = None

@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Send a message and get a response with RAG
    
    Args:
        request: Chat request with message and history
        background_tasks: FastAPI background tasks
        
    Returns:
        ChatResponse with answer and sources
    """
    try:
        # Validate input
        validator = ChatMessageValidator(
            message=request.message,
            session_id=request.session_id
        )
        
        logger.info(f"Chat request: {request.message[:100]}...")
        
        # Get or create session ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        
        # Initialize session if needed
        if session_id not in conversations:
            conversations[session_id] = {
                "created_at": datetime.now().isoformat(),
                "history": [],
                "message_count": 0
            }
        
        # Get LLM factory
        factory = get_llm_factory()
        
        # Retrieve relevant context from vector DB
        retriever = DocumentRetriever()
        context_data = retriever.retrieve_context(request.message)
        
        # Build messages for LLM
        messages = []
        
        # Add conversation history
        if request.conversation_history:
            for msg in request.conversation_history[-6:]:  # Last 6 messages
                messages.append(Message(role=msg.role, content=msg.content))
        
        # Add current query with context
        user_prompt = f"""Context information:
{context_data['context']}

Based on the above context, please answer the following question:

Question: {request.message}

Answer:"""
        
        messages.append(Message(role="user", content=user_prompt))
        
        # Get system prompt
        system_prompt = get_config().system_prompt
        
        # Generate response with fallback
        llm_response = factory.generate_with_fallback(
            messages=messages,
            system_prompt=system_prompt,
            preferred_provider=request.provider
        )
        
        # Store in conversation history
        conversations[session_id]["history"].extend([
            {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": "assistant",
                "content": llm_response.content,
                "timestamp": datetime.now().isoformat(),
                "provider": llm_response.provider
            }
        ])
        conversations[session_id]["message_count"] += 1
        
        # Cleanup old sessions in background
        background_tasks.add_task(cleanup_old_sessions)
        
        return ChatResponse(
            response=llm_response.content,
            sources=[Source(**src) for src in context_data['sources']],
            session_id=session_id,
            success=llm_response.finish_reason != "error",
            provider_used=llm_response.provider,
            tokens_used=llm_response.tokens_used
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """
    Stream chat responses for real-time interaction
    
    Args:
        request: Chat request
        
    Returns:
        Streaming response
    """
    try:
        validator = ChatMessageValidator(
            message=request.message,
            session_id=request.session_id
        )
        
        async def generate():
            try:
                # Get context
                retriever = DocumentRetriever()
                context_data = retriever.retrieve_context(request.message)
                
                # Build messages
                messages = []
                if request.conversation_history:
                    for msg in request.conversation_history[-6:]:
                        messages.append(Message(role=msg.role, content=msg.content))
                
                user_prompt = f"""Context: {context_data['context']}

Question: {request.message}

Answer:"""
                messages.append(Message(role="user", content=user_prompt))
                
                # Get provider
                factory = get_llm_factory()
                provider = factory.get_provider(request.provider) if request.provider else factory.get_default_provider()
                
                if not provider:
                    yield "data: Error: No provider available\n\n"
                    return
                
                # Stream response
                system_prompt = get_config().system_prompt
                async for token in provider.stream_response(messages, system_prompt):
                    yield f"data: {token}\n\n"
                
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}")
                yield f"data: Error: {str(e)}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"Stream setup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """
    Get conversation history for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Conversation history
    """
    if session_id not in conversations:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return conversations[session_id]

@router.delete("/history/{session_id}")
async def delete_history(session_id: str):
    """
    Delete conversation history
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    if session_id in conversations:
        del conversations[session_id]
        return {"message": "History deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@router.post("/feedback")
async def submit_feedback(
    session_id: str,
    message_id: str,
    helpful: bool,
    feedback: Optional[str] = None
):
    """
    Submit feedback for a response
    
    Args:
        session_id: Session identifier
        message_id: Message identifier
        helpful: Whether response was helpful
        feedback: Optional feedback text
        
    Returns:
        Success message
    """
    try:
        logger.info(f"Feedback: session={session_id}, helpful={helpful}")
        # Store feedback (implement database storage in production)
        return {"message": "Feedback received"}
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def cleanup_old_sessions():
    """Background task to cleanup old sessions"""
    try:
        current_time = datetime.now()
        expired = []
        
        for session_id, data in conversations.items():
            created_at = datetime.fromisoformat(data["created_at"])
            if (current_time - created_at).total_seconds() > 86400:  # 24 hours
                expired.append(session_id)
        
        for session_id in expired:
            del conversations[session_id]
            
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")