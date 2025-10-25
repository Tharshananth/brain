"""
Chat API endpoints - FIXED DATABASE SAVE VERSION
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import uuid
from datetime import datetime
import logging
import traceback

from llm.factory import get_llm_factory
from llm.base import Message, LLMResponse
from vector_db.retriever import DocumentRetriever
from utils.validators import ChatMessageValidator
from config import get_config
from database import get_db, FeedbackInteraction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory conversation storage
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


def save_to_database(db: Session, user_id: str, session_id: str, message_id: str,
                     question: str, response: str, provider: str, tokens: Optional[int]):
    """
    Separate function to save to database with proper error handling
    Returns: True if successful, False otherwise
    """
    try:
        logger.info("\n" + "=" * 80)
        logger.info("[DB_SAVE] Starting database save operation")
        logger.info("=" * 80)
        
        # Log all parameters
        logger.info(f"[DB_SAVE] user_id: {user_id}")
        logger.info(f"[DB_SAVE] session_id: {session_id}")
        logger.info(f"[DB_SAVE] message_id: {message_id}")
        logger.info(f"[DB_SAVE] question length: {len(question)}")
        logger.info(f"[DB_SAVE] response length: {len(response)}")
        logger.info(f"[DB_SAVE] provider: {provider}")
        logger.info(f"[DB_SAVE] tokens: {tokens}")
        
        # Create interaction object
        interaction = FeedbackInteraction(
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            question=question,
            response=response,
            provider_used=provider,
            tokens_used=tokens
        )
        
        logger.info(f"[DB_SAVE] Created FeedbackInteraction object with id: {interaction.id}")
        
        # Add to session
        db.add(interaction)
        logger.info("[DB_SAVE] Added to session")
        
        # Flush to check for errors
        db.flush()
        logger.info("[DB_SAVE] Flushed successfully")
        
        # Commit
        db.commit()
        logger.info("[DB_SAVE] COMMIT SUCCESSFUL!")
        
        # Refresh to get updated data
        db.refresh(interaction)
        logger.info(f"[DB_SAVE] Refreshed - Final DB ID: {interaction.id}")
        
        # Verify save
        verify = db.query(FeedbackInteraction).filter(
            FeedbackInteraction.message_id == message_id
        ).first()
        
        if verify:
            logger.info("[DB_SAVE] ✅✅✅ VERIFICATION SUCCESSFUL!")
            logger.info(f"[DB_SAVE] Found in DB with ID: {verify.id}")
            logger.info(f"[DB_SAVE] User: {verify.user_id}")
            logger.info(f"[DB_SAVE] Question: {verify.question[:50]}...")
            logger.info("=" * 80 + "\n")
            return True
        else:
            logger.error("[DB_SAVE] ❌ VERIFICATION FAILED - Record not found!")
            logger.error("=" * 80 + "\n")
            return False
            
    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("[DB_SAVE] ❌❌❌ DATABASE SAVE FAILED!")
        logger.error("=" * 80)
        logger.error(f"[DB_SAVE] Error type: {type(e).__name__}")
        logger.error(f"[DB_SAVE] Error message: {str(e)}")
        logger.error("[DB_SAVE] Full traceback:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80 + "\n")
        
        # Rollback on error
        try:
            db.rollback()
            logger.info("[DB_SAVE] Rollback completed")
        except Exception as rollback_error:
            logger.error(f"[DB_SAVE] Rollback failed: {rollback_error}")
        
        return False


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send a message and get a response with RAG
    """
    
    logger.info("\n" + "=" * 80)
    logger.info("NEW CHAT REQUEST")
    logger.info("=" * 80)
    logger.info(f"[REQUEST] Message: {request.message[:100]}...")
    logger.info(f"[REQUEST] User ID from request: {request.user_id}")
    logger.info(f"[REQUEST] Session ID from request: {request.session_id}")
    
    try:
        # Validate input
        validator = ChatMessageValidator(
            message=request.message,
            session_id=request.session_id
        )
        
        # Get or create session ID and user ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or "anonymous"
        
        logger.info(f"[SESSION] Final user_id: {user_id}")
        logger.info(f"[SESSION] Final session_id: {session_id}")
        
        # Generate unique message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        logger.info(f"[SESSION] Generated message_id: {message_id}")
        
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
        logger.info(f"[VECTOR_DB] Retrieved {len(context_data['sources'])} sources")
        
        # Build messages for LLM
        messages = []
        
        # Add conversation history (last 6 messages)
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
        logger.info("[LLM] Generating response...")
        llm_response = factory.generate_with_fallback(
            messages=messages,
            system_prompt=system_prompt,
            preferred_provider=request.provider
        )
        logger.info(f"[LLM] Response generated: {len(llm_response.content)} chars")
        logger.info(f"[LLM] Provider: {llm_response.provider}")
        logger.info(f"[LLM] Tokens: {llm_response.tokens_used}")
        
        # ===================================================================
        # CRITICAL: SAVE TO DATABASE - SIMPLIFIED AND FIXED
        # ===================================================================
        
        save_success = save_to_database(
            db=db,
            user_id=user_id,
            session_id=session_id,
            message_id=message_id,
            question=request.message,
            response=llm_response.content,
            provider=llm_response.provider,
            tokens=llm_response.tokens_used
        )
        
        if save_success:
            logger.info("[RESPONSE] ✅ Database save confirmed successful")
        else:
            logger.error("[RESPONSE] ❌ Database save failed but continuing with response")
        
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
        
        # Return response
        logger.info("[RESPONSE] Returning to client")
        logger.info("=" * 80 + "\n")
        
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
        logger.error("\n" + "=" * 80)
        logger.error("[ERROR] CHAT REQUEST FAILED")
        logger.error("=" * 80)
        logger.error(f"[ERROR] {e}")
        logger.error(traceback.format_exc())
        logger.error("=" * 80 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat responses for real-time interaction"""
    logger.info("[STREAM] Request received")
    
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
                logger.error(f"[STREAM] Error: {e}")
                yield f"data: Error: {str(e)}\n\n"
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        logger.error(f"[STREAM] Setup error: {e}")
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
            logger.info(f"[CLEANUP] Removed {len(expired)} expired sessions")
    except Exception as e:
        logger.error(f"[CLEANUP] Error: {e}")