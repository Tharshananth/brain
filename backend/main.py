"""
PingUs RAG Chatbot - Main Application
Production-ready FastAPI application with multi-model LLM support
"""
import os
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging
from contextlib import asynccontextmanager
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import get_config, get_api_config
from utils.logger import setup_logger
from routers import chat_router, documents_router, health_router, config_router
from vector_db.retriever import DocumentRetriever
from utils.document_loader import DocumentLoader

# Setup logging
logger = setup_logger("pingus")

# Load configuration
config = get_config()
api_config = get_api_config()

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup/shutdown events
    """
    # Startup
    logger.info("=" * 60)
    logger.info(f"Starting {config.app.name} v{config.app.version}")
    logger.info(f"Environment: {config.app.environment}")
    logger.info("=" * 60)
    
    try:
        # Initialize vector store with existing documents
        logger.info("Initializing vector store...")
        retriever = DocumentRetriever()
        doc_count = retriever.get_vector_store().get_document_count()
        
        if doc_count == 0:
            logger.info("No documents in vector store, loading from data directory...")
            data_dir = config.documents.data_dir
            docs = DocumentLoader.load_directory(data_dir)
            
            if docs:
                chunks = retriever.get_vector_store().add_documents(docs)
                logger.info(f"Loaded {len(docs)} documents ({chunks} chunks)")
            else:
                logger.warning("No documents found in data directory")
        else:
            logger.info(f"Vector store ready with {doc_count} documents")
        
        # Log available LLM providers
        from llm.factory import get_llm_factory
        factory = get_llm_factory()
        available = factory.get_available_providers()
        logger.info(f"Available LLM providers: {', '.join(available) if available else 'None'}")
        logger.info(f"Default provider: {config.llm.default_provider}")
        
        logger.info("Startup complete!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Startup error: {e}")
        logger.warning("Application started with errors")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")

# Create FastAPI app
app = FastAPI(
    title="PingUs RAG Chatbot",
    description="AI-powered chatbot with RAG capabilities",
    version="2.0.0",
    docs_url=None,  # Disable default docs URL
    redoc_url=None  # Disable default redoc URL
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
# Add CORS middleware
if api_config.cors.enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
    )
    logger.info("CORS enabled for all origins")

# Add GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

from fastapi.staticfiles import StaticFiles
import os

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
   
app.mount("/static", StaticFiles(directory="static"), name="static")

# Register routers
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(health_router)
app.include_router(config_router)

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint"""
    return {
        "name": config.app.name,
        "version": config.app.version,
        "status": "operational",
        "docs": "/docs"  # Changed from "/api/docs" to "/docs"
    }

# Health check (duplicate for convenience)
@app.get("/health", include_in_schema=False)
async def health():
    """Simple health check"""
    return {"status": "healthy"}


# Custom documentation endpoints
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="PingUs API Documentation",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="PingUs API Documentation",
    )
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    return get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if config.app.debug else "An error occurred"
        }
    )

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    
    port = api_config.port
    host = api_config.host
    reload = api_config.reload
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Reload mode: {reload}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload,
        log_level=config.logging.level.lower(),
        access_log=True
    )