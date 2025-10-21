import streamlit as st
import requests
from datetime import datetime
import json
from pathlib import Path
import time

# Configuration
API_BASE_URL = "http://localhost:8000"
st.set_page_config(
    page_title="VoxelBox RAG Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #e3f2fd;
        margin-left: 20%;
        color: #000000;
    }
    .assistant-message {
        background-color: #f5f5f5;
        margin-right: 20%;
        color: #000000;
    }
    .message-content {
        color: #000000;
        font-size: 1rem;
        line-height: 1.6;
    }
    .source-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 0.3rem;
        border-left: 4px solid #ffc107;
        margin-top: 0.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"session_{int(time.time())}"
if 'current_provider' not in st.session_state:
    st.session_state.current_provider = None
if 'available_providers' not in st.session_state:
    st.session_state.available_providers = []

# Helper Functions
def check_server_health():
    """Check if backend server is running"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_config():
    """Get current configuration"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/config/")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_providers():
    """Get available LLM providers"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/config/providers")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def switch_provider(provider_name):
    """Switch to different LLM provider"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/config/provider/{provider_name}")
        return response.status_code == 200
    except:
        return False

def send_message(message, provider=None):
    """Send message to chat API"""
    try:
        payload = {
            "message": message,
            "conversation_history": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages[-10:]  # Last 10 messages
            ],
            "session_id": st.session_state.session_id,
            "provider": provider
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/chat/",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Error: {str(e)}")
    return None

def stream_message(message, provider=None):
    """Stream message response"""
    try:
        payload = {
            "message": message,
            "conversation_history": [
                {"role": msg["role"], "content": msg["content"]}
                for msg in st.session_state.messages[-10:]
            ],
            "session_id": st.session_state.session_id,
            "provider": provider
        }
        
        response = requests.post(
            f"{API_BASE_URL}/api/chat/stream",
            json=payload,
            stream=True,
            timeout=120
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        chunk = line_text[6:]
                        if chunk != '[DONE]':
                            yield chunk
    except Exception as e:
        yield f"Error: {str(e)}"

def list_documents():
    """List all documents"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/documents/")
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def upload_document(file):
    """Upload document"""
    try:
        files = {'file': (file.name, file, file.type)}
        response = requests.post(
            f"{API_BASE_URL}/api/documents/upload",
            files=files,
            timeout=120
        )
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Upload error: {str(e)}")
        return None

def delete_document(filename):
    """Delete document"""
    try:
        response = requests.delete(f"{API_BASE_URL}/api/documents/{filename}")
        return response.status_code == 200
    except:
        return False

def refresh_knowledge_base():
    """Refresh knowledge base"""
    try:
        response = requests.post(f"{API_BASE_URL}/api/documents/refresh")
        return response.json() if response.status_code == 200 else None
    except:
        return None

def clear_chat():
    """Clear chat history"""
    st.session_state.messages = []
    st.session_state.session_id = f"session_{int(time.time())}"

# Sidebar
with st.sidebar:
    st.markdown("### 🧠 VoxelBox RAG Chatbot")
    st.markdown("---")
    
    # Server Status
    server_healthy = check_server_health()
    if server_healthy:
        st.success("✅ Server Online")
    else:
        st.error("❌ Server Offline")
        st.stop()
    
    # Get configuration
    config = get_config()
    if config:
        st.info(f"📦 Version: {config['app']['version']}")
    
    # Provider Selection
    st.markdown("### 🤖 LLM Provider")
    providers = get_providers()
    if providers:
        st.session_state.available_providers = providers
        provider_names = [p['name'] for p in providers]
        
        current_provider = st.selectbox(
            "Select Provider",
            provider_names,
            index=provider_names.index(config['current_provider']) if config else 0,
            key="provider_select"
        )
        
        if current_provider != st.session_state.current_provider:
            if switch_provider(current_provider):
                st.session_state.current_provider = current_provider
                st.success(f"Switched to {current_provider}")
                st.rerun()
    
    # Display provider info
    if providers:
        current = next((p for p in providers if p['name'] == current_provider), None)
        if current:
            st.markdown(f"**Model:** `{current['model']}`")
    
    st.markdown("---")
    
    # Session Info
    st.markdown("### 💬 Chat Session")
    st.text(f"ID: {st.session_state.session_id[:12]}...")
    st.text(f"Messages: {len(st.session_state.messages)}")
    
    if st.button("🔄 New Chat", use_container_width=True):
        clear_chat()
        st.rerun()
    
    st.markdown("---")
    
    # Document Stats
    docs = list_documents()
    st.markdown("### 📚 Knowledge Base")
    st.metric("Documents", len(docs))
    
    if st.button("♻️ Refresh KB", use_container_width=True):
        with st.spinner("Refreshing..."):
            result = refresh_knowledge_base()
            if result:
                st.success(f"✅ {result['documents']} docs, {result['chunks']} chunks")
                st.rerun()

# Main Content Tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📄 Documents", "⚙️ Settings"])

# TAB 1: Chat Interface
with tab1:
    st.markdown('<div class="main-header">VoxelBox Explore Assistant</div>', unsafe_allow_html=True)
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Display chat messages
        for idx, message in enumerate(st.session_state.messages):
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                st.markdown(f"""
                <div class="chat-message user-message">
                    <strong style="color: #1565c0;">👤 You</strong>
                    <div class="message-content">{content}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant-message">
                    <strong style="color: #2e7d32;">🤖 Assistant</strong>
                    <div class="message-content">{content}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show sources if available
                if "sources" in message and message["sources"]:
                    with st.expander("📚 Sources Used"):
                        for src in message["sources"]:
                            st.markdown(f"""
                            <div class="source-box">
                                <strong>📄 {src['title']}</strong><br>
                                {src['content']}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Show metadata
                if "provider" in message:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"Provider: {message['provider']}")
                    with col2:
                        if "tokens" in message and message["tokens"]:
                            st.caption(f"Tokens: {message['tokens']}")
    
    # Chat input
    st.markdown("---")
    
    # Use a form to prevent auto-submission
    with st.form(key="chat_form", clear_on_submit=True):
        col1, col2 = st.columns([6, 1])
        
        with col1:
            user_input = st.text_input(
                "Ask a question...",
                placeholder="e.g., What is VoxelBox Explore?",
                key="chat_input",
                label_visibility="collapsed"
            )
        
        with col2:
            use_streaming = st.checkbox("Stream", value=True)
        
        submit_button = st.form_submit_button("📤 Send", use_container_width=True, type="primary")
    
    if submit_button and user_input:
        if user_input.strip():  # Only process non-empty messages
            # Add user message
            st.session_state.messages.append({
                "role": "user",
                "content": user_input.strip()
            })
            
            # Get response
            if use_streaming:
                # Streaming response
                with st.spinner("Thinking..."):
                    response_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in stream_message(user_input, st.session_state.current_provider):
                        full_response += chunk
                        response_placeholder.markdown(f"🤖 {full_response}▌")
                    
                    response_placeholder.markdown(f"🤖 {full_response}")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "provider": st.session_state.current_provider or "unknown"
                    })
            else:
                # Standard response
                with st.spinner("Getting response..."):
                    result = send_message(user_input, st.session_state.current_provider)
                    
                    if result:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["response"],
                            "sources": result.get("sources", []),
                            "provider": result.get("provider_used", "unknown"),
                            "tokens": result.get("tokens_used")
                        })
            
            st.rerun()

# TAB 2: Document Management
with tab2:
    st.markdown("## 📄 Document Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Upload Documents")
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'docx', 'txt', 'md'],
            accept_multiple_files=True,
            help="Supported formats: PDF, DOCX, TXT, MD (Max 10MB)"
        )
        
        if uploaded_files:
            if st.button("⬆️ Upload All", type="primary"):
                progress_bar = st.progress(0)
                for idx, file in enumerate(uploaded_files):
                    with st.spinner(f"Uploading {file.name}..."):
                        result = upload_document(file)
                        if result:
                            st.success(f"✅ {file.name} - {result['chunks']} chunks")
                        else:
                            st.error(f"❌ Failed to upload {file.name}")
                    progress_bar.progress((idx + 1) / len(uploaded_files))
                st.rerun()
    
    with col2:
        st.markdown("### Quick Actions")
        if st.button("♻️ Refresh Knowledge Base", use_container_width=True):
            with st.spinner("Refreshing..."):
                result = refresh_knowledge_base()
                if result:
                    st.success(f"✅ Done!\n\nDocs: {result['documents']}\nChunks: {result['chunks']}")
                    st.rerun()
    
    st.markdown("---")
    st.markdown("### 📚 Current Documents")
    
    docs = list_documents()
    
    if not docs:
        st.info("No documents uploaded yet. Upload some documents to get started!")
    else:
        for doc in docs:
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                st.markdown(f"**📄 {doc['name']}**")
            with col2:
                size_mb = doc['size'] / (1024 * 1024)
                st.text(f"{size_mb:.2f} MB")
            with col3:
                st.text(doc['type'])
            with col4:
                if st.button("🗑️", key=f"delete_{doc['name']}"):
                    if delete_document(doc['name']):
                        st.success(f"Deleted {doc['name']}")
                        st.rerun()
                    else:
                        st.error("Delete failed")

# TAB 3: Settings & Configuration
with tab3:
    st.markdown("## ⚙️ Settings & Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🤖 LLM Providers")
        providers = get_providers()
        
        if providers:
            for provider in providers:
                with st.expander(f"**{provider['name'].upper()}**"):
                    st.markdown(f"**Model:** `{provider['model']}`")
                    st.markdown(f"**Temperature:** {provider.get('temperature', 'N/A')}")
                    st.markdown(f"**Max Tokens:** {provider.get('max_tokens', 'N/A')}")
                    
                    if st.button(f"Use {provider['name']}", key=f"use_{provider['name']}"):
                        if switch_provider(provider['name']):
                            st.success(f"Switched to {provider['name']}")
                            st.rerun()
        else:
            st.warning("No providers available")
    
    with col2:
        st.markdown("### 📊 System Status")
        
        config = get_config()
        if config:
            st.markdown(f"**App:** {config['app']['name']}")
            st.markdown(f"**Version:** {config['app']['version']}")
            st.markdown(f"**Environment:** {config['app']['environment']}")
            st.markdown(f"**Current Provider:** {config['current_provider']}")
            st.markdown(f"**Embedding Provider:** {config['embedding_provider']}")
            st.markdown(f"**Vector DB:** {config['vector_db']['type']}")
        
        st.markdown("---")
        st.markdown("### 🏥 Health Check")
        
        if st.button("🔍 Check Health", use_container_width=True):
            try:
                response = requests.get(f"{API_BASE_URL}/api/health/")
                if response.status_code == 200:
                    health = response.json()
                    st.json(health)
                else:
                    st.error("Health check failed")
            except:
                st.error("Cannot reach server")
    
    st.markdown("---")
    st.markdown("### 📝 System Prompt")
    
    if st.button("👁️ View System Prompt"):
        try:
            response = requests.get(f"{API_BASE_URL}/api/config/system-prompt")
            if response.status_code == 200:
                prompt = response.json()
                st.text_area("System Prompt", prompt['system_prompt'], height=300)
        except:
            st.error("Failed to fetch system prompt")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>VoxelBox Explore Assistant | Powered by RAG & Multi-Model LLM</small>
</div>
""", unsafe_allow_html=True)