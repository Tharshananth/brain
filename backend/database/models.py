"""Database models for feedback system"""
from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class FeedbackInteraction(Base):
    """Store chat interactions and feedback"""
    __tablename__ = 'feedback_interactions'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)  # NEW: User identification
    session_id = Column(String, nullable=False, index=True)
    message_id = Column(String, nullable=False, unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Interaction data
    question = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    provider_used = Column(String)
    tokens_used = Column(Integer)
    
    # Feedback data
    feedback_type = Column(String)  # 'thumbs_up', 'thumbs_down', or NULL
    feedback_comment = Column(Text)  # Optional comment
    feedback_timestamp = Column(DateTime)
    
    def __repr__(self):
        return f"<FeedbackInteraction(id={self.id}, feedback_type={self.feedback_type})>"