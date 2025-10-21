"""
Base LLM Provider Interface
Defines the contract for all LLM providers
"""
from abc import ABC, abstractmethod
from typing import List, Optional, AsyncIterator, Dict, Any
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MessageRole(str, Enum):
    """Message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

@dataclass
class Message:
    """Chat message"""
    role: str
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}

@dataclass
class LLMResponse:
    """Response from LLM"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None

class BaseLLMProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        top_p: float = 0.9,
        timeout: int = 30,
        **kwargs
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.timeout = timeout
        self.extra_params = kwargs
        self.client = None
        
        # Validate configuration
        self.validate_config()
    
    @abstractmethod
    def validate_config(self) -> None:
        """Validate provider configuration and initialize client"""
        pass
    
    @abstractmethod
    def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a response from the LLM
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters
            
        Returns:
            LLMResponse object
        """
        pass
    
    @abstractmethod
    async def stream_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream response from the LLM
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system prompt
            **kwargs: Additional provider-specific parameters
            
        Yields:
            Response text chunks
        """
        pass
    
    def format_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Format messages for the provider
        
        Args:
            messages: List of Message objects
            system_prompt: Optional system prompt
            
        Returns:
            List of formatted message dictionaries
        """
        formatted = []
        
        # Add system prompt if provided
        if system_prompt:
            formatted.append({
                "role": "system",
                "content": system_prompt
            })
        
        # Add conversation messages
        for msg in messages:
            formatted.append(msg.to_dict())
        
        return formatted
    
    def _handle_error(self, error: Exception, operation: str) -> LLMResponse:
        """
        Handle errors and return error response
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            
        Returns:
            LLMResponse with error information
        """
        error_msg = f"{operation} failed: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        return LLMResponse(
            content="I apologize, but I encountered an error processing your request. Please try again.",
            model=self.model,
            provider=self.__class__.__name__.replace("Provider", "").lower(),
            finish_reason="error",
            error=error_msg
        )
    
    def get_info(self) -> Dict[str, Any]:
        """Get provider information"""
        return {
            "provider": self.__class__.__name__.replace("Provider", "").lower(),
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }