"""Google Gemini 2.5 Flash LLM Provider - Based on Working Pattern"""
from typing import List, Optional, AsyncIterator
import google.generativeai as genai
from .base import BaseLLMProvider, Message, LLMResponse
import logging

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """Google Gemini 2.5 Flash provider"""
    
    def validate_config(self) -> None:
        """Initialize Gemini client - simple like your working code"""
        if not self.api_key:
            raise ValueError("Google API key is required")
        
        # Configure API
        genai.configure(api_key=self.api_key)
        
        # Initialize model - NO safety settings, just like your working code
        self.client = genai.GenerativeModel(self.model)
        logger.info(f"✅ Initialized Gemini model: {self.model}")
    
    def _build_prompt_from_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> str:
        """Build a single prompt string from messages - like your working code"""
        
        # Start with system prompt if provided (use full prompt from config.yaml)
        prompt = ""
        if system_prompt:
            prompt = system_prompt + "\n\n"
        
        # Add conversation history
        for msg in messages:
            if msg.role == "user":
                prompt += f"User: {msg.content}\n\n"
            elif msg.role == "assistant":
                prompt += f"Assistant: {msg.content}\n\n"
        
        return prompt.strip()
    
    def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate response - exactly like your working code"""
        try:
            # Build single prompt string
            final_prompt = self._build_prompt_from_messages(messages, system_prompt)
            
            logger.debug(f"Prompt: {final_prompt[:200]}...")
            
            # Generate content - simple, like your code
            response = self.client.generate_content(final_prompt)
            
            # Get text
            if response and response.text:
                logger.info(f"✅ Generated {len(response.text)} chars")
                return LLMResponse(
                    content=response.text,
                    model=self.model,
                    provider="gemini",
                    tokens_used=None,
                    finish_reason="stop"
                )
            else:
                logger.warning("Empty response from Gemini")
                return LLMResponse(
                    content="I apologize, but I couldn't generate a response. Please try again.",
                    model=self.model,
                    provider="gemini",
                    finish_reason="error",
                    error="Empty response"
                )
            
        except Exception as e:
            logger.error(f"Gemini error: {e}", exc_info=True)
            return self._handle_error(e, "generate_response")
    
    async def stream_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream response - same pattern as your working code"""
        try:
            # Build single prompt string
            final_prompt = self._build_prompt_from_messages(messages, system_prompt)
            
            logger.debug(f"Streaming prompt: {final_prompt[:200]}...")
            
            # Generate with streaming - simple like your code
            response = self.client.generate_content(final_prompt, stream=True)
            
            # Yield chunks
            chunk_count = 0
            for chunk in response:
                if chunk.text:
                    chunk_count += 1
                    yield chunk.text
            
            if chunk_count > 0:
                logger.info(f"✅ Streamed {chunk_count} chunks")
            else:
                logger.warning("No chunks received")
                yield "I apologize, but I couldn't generate a response. Please try again."
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"Error: I encountered an issue. Please try again."