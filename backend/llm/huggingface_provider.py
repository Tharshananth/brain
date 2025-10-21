"""HuggingFace LLM Provider Implementation"""
from typing import List, Optional, AsyncIterator
from huggingface_hub import InferenceClient
from .base import BaseLLMProvider, Message, LLMResponse
import logging

logger = logging.getLogger(__name__)

class HuggingFaceProvider(BaseLLMProvider):
    """HuggingFace Inference API provider"""
    
    def validate_config(self) -> None:
        if not self.api_key:
            raise ValueError("HuggingFace token is required")
        self.client = InferenceClient(token=self.api_key)
    
    def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        try:
            formatted_messages = self.format_messages(messages, system_prompt)
            
            response = self.client.chat_completion(
                messages=formatted_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                **kwargs
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=self.model,
                provider="huggingface",
                tokens_used=None,
                finish_reason=response.choices[0].finish_reason
            )
        except Exception as e:
            return self._handle_error(e, "generate_response")
    
    async def stream_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        try:
            formatted_messages = self.format_messages(messages, system_prompt)
            
            stream = self.client.chat_completion(
                messages=formatted_messages,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"
