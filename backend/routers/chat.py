"""
Chat API endpoints - COMPLETE FIXED VERSION
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, AsyncIterator
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
import logging

from llm.factory import get_llm_factory
from llm.base import Message, LLMResponse
from vector_db.retriever import DocumentRetriever
from utils.validators import ChatMessageValidator
from config import get_config
from database import get_db, FeedbackInteraction

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
    provider: Optional[str] = None
    user_id: Optional[str] = None

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
    message_id: str

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send a message and get a response with RAG
    """
    try:
        # Validate input
        validator = ChatMessageValidator(
            message=request.message,
            session_id=request.session_id
        )
        
        logger.info(f"Chat request: {request.message[:100]}...")
        
        # Get or create session ID and user ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or "anonymous"
        
        logger.info(f"📝 Session: {session_id}, User: {user_id}")
        
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
            for msg in request.conversation_history[-6:]:
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
        
        # Generate unique message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        
        # Store interaction in database - WITH DEBUG LOGGING
        logger.info(f"🔍 Attempting to save interaction to database...")
        logger.info(f"   Message ID: {message_id}")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   Database session: {db}")
        
        try:
            # Create interaction object
            interaction = FeedbackInteraction(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                question=request.message,
                response=llm_response.content,
                provider_used=llm_response.provider,
                tokens_used=llm_response.tokens_used
            )
            
            logger.info(f"   ✅ Created FeedbackInteraction object")
            
            # Add to session
            db.add(interaction)
            logger.info(f"   ✅ Added to database session")
            
            # Commit
            db.commit()
            logger.info(f"   ✅ Committed to database")
            
            # Refresh to get the ID
            db.refresh(interaction)
            logger.info(f"   ✅ Refreshed object - DB ID: {interaction.id}")
            
            # Verify it's actually in the database
            from database.connection import SessionLocal
            verify_db = SessionLocal()
            check = verify_db.query(FeedbackInteraction).filter(
                FeedbackInteraction.message_id == message_id
            ).first()
            verify_db.close()
            
            if check:
                logger.info(f"✅✅✅ VERIFIED: Interaction {message_id} found in database!")
            else:
                logger.error(f"❌❌❌ WARNING: Interaction {message_id} NOT found after commit!")
            
        except Exception as e:
            logger.error(f"❌ Failed to store interaction: {e}", exc_info=True)
            db.rollback()
            logger.error(f"   Database rolled back")
            # Continue anyway - don't fail the chat request
        
        # Store in conversation history
        conversations[session_id]["history"].extend([
            {
                "id": f"user_{uuid.uuid4().hex[:8]}",
                "role": "user",
                "content": request.message,
                "timestamp": datetime.now().isoformat()
            },
            {
                "id": message_id,
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
            tokens_used=llm_response.tokens_used,
            message_id=message_id
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses for real-time interaction"""
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
    """Get conversation history for a session"""
    if session_id not in conversations:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return conversations[session_id]

@router.delete("/history/{session_id}")
async def delete_history(session_id: str):
    """Delete conversation history"""
    if session_id in conversations:
        del conversations[session_id]
        return {"message": "History deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

def cleanup_old_sessions():
    """Background task to cleanup old sessions"""
    try:
        current_time = datetime.now()
        expired = []
        
        for session_id, data in conversations.items():
            created_at = datetime.fromisoformat(data["created_at"])
            if (current_time - created_at).total_seconds() > 86400:
                expired.append(session_id)
        
        for session_id in expired:
            del conversations[session_id]
            
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")