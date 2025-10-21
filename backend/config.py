"""
Configuration Management for PingUs RAG Chatbot
Loads and validates configuration from config.yaml
"""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AppConfig(BaseModel):
    name: str
    version: str
    environment: str
    debug: bool

class ProviderConfig(BaseModel):
    enabled: bool
    model: str
    api_key_env: str
    temperature: float
    max_tokens: int
    top_p: float
    stream: bool
    timeout: int
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0

class LLMConfig(BaseModel):
    default_provider: str
    enable_fallback: bool
    fallback_order: List[str]
    providers: Dict[str, ProviderConfig]

class EmbeddingProviderConfig(BaseModel):
    model: str
    api_key_env: str
    dimensions: int

class EmbeddingsConfig(BaseModel):
    provider: str
    providers: Dict[str, EmbeddingProviderConfig]

class VectorDBSearchConfig(BaseModel):
    k: int
    score_threshold: float
    search_type: str

class VectorDBChunkingConfig(BaseModel):
    chunk_size: int
    chunk_overlap: int
    separators: List[str]

class VectorDBConfig(BaseModel):
    type: str
    persist_directory: str
    collection_name: str
    search: VectorDBSearchConfig
    chunking: VectorDBChunkingConfig

class DocumentsConfig(BaseModel):
    supported_formats: List[str]
    max_file_size: int
    data_dir: str
    upload_dir: str

class CORSConfig(BaseModel):
    enabled: bool
    allow_origins: List[str]
    allow_credentials: bool
    allow_methods: List[str]
    allow_headers: List[str]

class RateLimitConfig(BaseModel):
    enabled: bool
    requests_per_minute: int
    requests_per_hour: int

class APIConfig(BaseModel):
    host: str
    port: int
    reload: bool
    cors: CORSConfig
    rate_limit: RateLimitConfig
    timeout: int

class CacheConfig(BaseModel):
    enabled: bool
    type: str
    ttl: int
    max_size: int

class LogFileConfig(BaseModel):
    enabled: bool
    path: str
    max_bytes: int
    backup_count: int

class LogConsoleConfig(BaseModel):
    enabled: bool
    colorize: bool

class LoggingConfig(BaseModel):
    level: str
    format: str
    file: LogFileConfig
    console: LogConsoleConfig

class SessionConfig(BaseModel):
    timeout: int
    cleanup_interval: int
    max_sessions: int

class AlertsConfig(BaseModel):
    error_rate_threshold: float
    response_time_threshold: int
    token_usage_threshold: int

class MonitoringConfig(BaseModel):
    enabled: bool
    track_usage: bool
    track_costs: bool
    track_performance: bool
    alerts: AlertsConfig

class Config(BaseModel):
    app: AppConfig
    llm: LLMConfig
    embeddings: EmbeddingsConfig
    vector_db: VectorDBConfig
    documents: DocumentsConfig
    api: APIConfig
    cache: CacheConfig
    logging: LoggingConfig
    session: SessionConfig
    system_prompt: str
    monitoring: MonitoringConfig

# Global config instance
_config: Optional[Config] = None




def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file"""
    global _config
    
    if _config is not None:
        return _config
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except UnicodeDecodeError as e:
        raise RuntimeError(f"Error reading config file: Please ensure {config_path} is saved with UTF-8 encoding") from e
    
    _config = Config(**config_data)
    return _config




def get_config() -> Config:
    """Get loaded configuration"""
    if _config is None:
        return load_config()
    return _config

def get_api_config() -> APIConfig:
    """Get API configuration"""
    return get_config().api

def get_llm_config() -> LLMConfig:
    """Get LLM configuration"""
    return get_config().llm

def get_logging_config() -> LoggingConfig:
    """Get logging configuration"""
    return get_config().logging

def get_provider_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider from environment"""
    config = get_config()
    provider_config = config.llm.providers.get(provider)
    
    if not provider_config:
        return None
    
    api_key = os.getenv(provider_config.api_key_env)
    return api_key

def get_embedding_api_key() -> Optional[str]:
    """Get API key for embeddings provider"""
    config = get_config()
    provider = config.embeddings.provider
    provider_config = config.embeddings.providers.get(provider)
    
    if not provider_config:
        return None
    
    return os.getenv(provider_config.api_key_env)