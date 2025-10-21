"""Google Gemini LLM Provider Implementation"""
from typing import List, Optional, AsyncIterator
import google.generativeai as genai
from .base import BaseLLMProvider, Message, LLMResponse
import logging

logger = logging.getLogger(__name__)

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider"""
    
    def validate_config(self) -> None:
        if not self.api_key:
            raise ValueError("Google API key is required")
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model)
    
    def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        try:
            # Format conversation for Gemini
            chat_history = []
            for msg in messages[:-1]:  # All but last message
                role = "user" if msg.role == "user" else "model"
                chat_history.append({"role": role, "parts": [msg.content]})
            
            # Start chat with history
            chat = self.client.start_chat(history=chat_history)
            
            # Send current message
            response = chat.send_message(
                messages[-1].content,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                )
            )
            
            return LLMResponse(
                content=response.text,
                model=self.model,
                provider="gemini",
                tokens_used=None,  # Gemini doesn't provide token counts easily
                finish_reason="stop"
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
            chat_history = []
            for msg in messages[:-1]:
                role = "user" if msg.role == "user" else "model"
                chat_history.append({"role": role, "parts": [msg.content]})
            
            chat = self.client.start_chat(history=chat_history)
            
            response = chat.send_message(
                messages[-1].content,
                generation_config=genai.types.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                ),
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"Error: {str(e)}"

