"""Test Gemini using the exact pattern that works for you"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from llm.gemini_provider import GeminiProvider
from llm.base import Message
import os
import asyncio

print("=" * 60)
print("TESTING GEMINI PROVIDER - YOUR WORKING PATTERN")
print("=" * 60)

# Initialize provider
provider = GeminiProvider(
    api_key=os.getenv('GOOGLE_API_KEY'),
    model='gemini-2.5-flash',
    temperature=0.7,
    max_tokens=500,
    top_p=0.9
)

# Test 1: Simple question (like your working code)
print("\nTest 1: Simple Question")
print("-" * 60)
messages = [Message(role="user", content="What is fMRI?")]
response = provider.generate_response(messages)
print(f"✅ Response: {response.content[:200]}...")
print(f"   Provider: {response.provider}")
print(f"   Finish reason: {response.finish_reason}")

# Test 2: With conversation history
print("\nTest 2: With Conversation History")
print("-" * 60)
messages = [
    Message(role="user", content="What is MRI?"),
    Message(role="assistant", content="MRI (Magnetic Resonance Imaging) is a medical imaging technique."),
    Message(role="user", content="How does it work?")
]
response = provider.generate_response(messages)
print(f"✅ Response: {response.content[:200]}...")

# Test 3: Streaming
print("\nTest 3: Streaming Response")
print("-" * 60)
async def test_stream():
    messages = [Message(role="user", content="Explain diffusion MRI briefly")]
    print("Streaming: ", end='', flush=True)
    
    chunk_count = 0
    async for chunk in provider.stream_response(messages):
        chunk_count += 1
        print(chunk, end='', flush=True)
    
    print(f"\n✅ Received {chunk_count} chunks")

asyncio.run(test_stream())

# Test 4: Neuroimaging question (like yours)
print("\nTest 4: Neuroimaging Question")
print("-" * 60)
messages = [Message(role="user", content="Explain how fMRI differs from PET in measuring brain activity.")]
response = provider.generate_response(messages)
print(f"✅ Response:\n{response.content}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE!")
print("=" * 60)