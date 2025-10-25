"""
Chat API endpoints - WINDOWS COMPATIBLE VERSION
No emoji characters that cause encoding errors on Windows
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


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send a message and get a response with RAG
    """
    
    # Log EVERYTHING (no emojis for Windows compatibility)
    logger.info("\n" + "=" * 80)
    logger.info("NEW CHAT REQUEST RECEIVED")
    logger.info("=" * 80)
    logger.info(f"[MESSAGE] {request.message[:100]}...")
    logger.info(f"[USER_ID] Request: {request.user_id}")
    logger.info(f"[SESSION_ID] Request: {request.session_id}")
    logger.info(f"[PROVIDER] Requested: {request.provider}")
    
    try:
        # Validate input
        validator = ChatMessageValidator(
            message=request.message,
            session_id=request.session_id
        )
        logger.info("[OK] Input validation passed")
        
        # Get or create session ID and user ID
        session_id = request.session_id or f"session_{uuid.uuid4().hex[:12]}"
        user_id = request.user_id or "anonymous"
        
        logger.info(f"[USER] Using user_id: {user_id}")
        logger.info(f"[SESSION] Using session_id: {session_id}")
        
        # Generate unique message ID
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        logger.info(f"[MSG_ID] Generated: {message_id}")
        
        # Initialize session if needed
        if session_id not in conversations:
            conversations[session_id] = {
                "created_at": datetime.now().isoformat(),
                "history": [],
                "message_count": 0
            }
            logger.info("[SESSION] Created new conversation")
        
        # Get LLM factory
        logger.info("[LLM] Getting factory...")
        factory = get_llm_factory()
        logger.info("[LLM] Factory ready")
        
        # Retrieve relevant context from vector DB
        logger.info("[VECTOR_DB] Retrieving context...")
        retriever = DocumentRetriever()
        context_data = retriever.retrieve_context(request.message)
        logger.info(f"[VECTOR_DB] Retrieved {len(context_data['sources'])} sources")
        
        # Build messages for LLM
        messages = []
        
        # Add conversation history
        if request.conversation_history:
            for msg in request.conversation_history[-6:]:
                messages.append(Message(role=msg.role, content=msg.content))
            logger.info(f"[HISTORY] Added {len(messages)} messages")
        
        # Add current query with context
        user_prompt = f"""Context information:
{context_data['context']}

Based on the above context, please answer the following question:

Question: {request.message}

Answer:"""
        
        messages.append(Message(role="user", content=user_prompt))
        logger.info(f"[PROMPT] Built with {len(messages)} total messages")
        
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
        # CRITICAL SECTION: DATABASE SAVE
        # ===================================================================
        logger.info("\n" + "=" * 80)
        logger.info("DATABASE SAVE STARTING")
        logger.info("=" * 80)
        
        try:
            logger.info("[DB] Save parameters:")
            logger.info(f"[DB]   user_id: {user_id}")
            logger.info(f"[DB]   session_id: {session_id}")
            logger.info(f"[DB]   message_id: {message_id}")
            logger.info(f"[DB]   question length: {len(request.message)} chars")
            logger.info(f"[DB]   response length: {len(llm_response.content)} chars")
            logger.info(f"[DB]   provider: {llm_response.provider}")
            logger.info(f"[DB]   tokens: {llm_response.tokens_used}")
            
            # Check database session
            logger.info(f"[DB] Session object: {db}")
            logger.info(f"[DB] Session type: {type(db)}")
            logger.info(f"[DB] Session active: {db.is_active}")
            
            # Create interaction object
            logger.info("[DB] Creating FeedbackInteraction object...")
            interaction = FeedbackInteraction(
                user_id=user_id,
                session_id=session_id,
                message_id=message_id,
                question=request.message,
                response=llm_response.content,
                provider_used=llm_response.provider,
                tokens_used=llm_response.tokens_used
            )
            logger.info("[DB] [OK] FeedbackInteraction object created")
            logger.info(f"[DB]   Object id: {interaction.id}")
            logger.info(f"[DB]   Object user_id: {interaction.user_id}")
            logger.info(f"[DB]   Object message_id: {interaction.message_id}")
            
            # Add to session
            logger.info("[DB] Adding to database session...")
            db.add(interaction)
            logger.info("[DB] [OK] Added to session")
            
            # Flush to check for errors before commit
            logger.info("[DB] Flushing session...")
            db.flush()
            logger.info("[DB] [OK] Flushed successfully")
            
            # Commit
            logger.info("[DB] Committing transaction...")
            db.commit()
            logger.info("[DB] [OK] COMMIT SUCCESSFUL!")
            
            # Refresh
            logger.info("[DB] Refreshing object...")
            db.refresh(interaction)
            logger.info(f"[DB] [OK] Refreshed - Final DB ID: {interaction.id}")
            
            # VERIFICATION - Check if really saved
            logger.info("[DB] VERIFYING save in database...")
            verify_interaction = db.query(FeedbackInteraction).filter(
                FeedbackInteraction.message_id == message_id
            ).first()
            
            if verify_interaction:
                logger.info("[DB] [SUCCESS] VERIFICATION PASSED!")
                logger.info(f"[DB]   Found in DB with ID: {verify_interaction.id}")
                logger.info(f"[DB]   User: {verify_interaction.user_id}")
                logger.info(f"[DB]   Question: {verify_interaction.question[:50]}...")
                logger.info("=" * 80)
                logger.info("[DB] DATABASE SAVE COMPLETELY SUCCESSFUL!")
                logger.info("=" * 80 + "\n")
            else:
                logger.error("[DB] [ERROR] VERIFICATION FAILED!")
                logger.error(f"[DB]   Message {message_id} NOT FOUND in database!")
                logger.error("[DB]   This should be impossible after successful commit!")
                logger.error("=" * 80 + "\n")
                
        except Exception as db_error:
            logger.error("\n" + "=" * 80)
            logger.error("[DB] [ERROR] DATABASE SAVE FAILED!")
            logger.error("=" * 80)
            logger.error(f"[DB] Error type: {type(db_error).__name__}")
            logger.error(f"[DB] Error message: {str(db_error)}")
            logger.error("[DB] Full traceback:")
            logger.error(traceback.format_exc())
            logger.error("=" * 80 + "\n")
            
            # Rollback
            logger.error("[DB] Rolling back transaction...")
            db.rollback()
            logger.error("[DB] Rollback complete")
            
            # DO NOT fail the request - just log the error
            logger.error("[DB] [WARNING] Continuing to return response despite save failure")
        
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
        logger.info("[MEMORY] Saved to in-memory conversation history")
        
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