# routers/__init__.py
"""API Routers Package"""
from .chat import router as chat_router
from .documents import router as documents_router
from .health import router as health_router
from .config import router as config_router

__all__ = ['chat_router', 'documents_router', 'health_router', 'config_router']
