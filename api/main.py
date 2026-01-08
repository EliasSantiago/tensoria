"""
Tensoria API - Open Source LLM API Infrastructure

FastAPI application that provides an OpenAI-compatible API for LLM inference via Ollama.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys

from .config import get_settings
from .routes import chat, completions, models, health

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)
logger.info("Loading Tensoria API module...")

# Determine if we're in production mode (API key is set)
is_production = bool(settings.api_key)

# Create FastAPI app
app = FastAPI(
    title="Tensoria API",
    description="""
## Open Source LLM API Infrastructure

Tensoria provides an OpenAI-compatible API for open source LLM inference via Ollama.

### Features

- **OpenAI-compatible endpoints** - Drop-in replacement for OpenAI API
- **Multiple model support** - Mistral, DeepSeek, Qwen, and more
- **No automatic downloads** - Full control over which models are installed
- **Health monitoring** - Built-in health check endpoints
- **API Key authentication** - Secure access control

### Supported Models

Models must be installed manually. Supported models include:
- `mistral` / `mistral:7b`
- `deepseek-coder` / `deepseek-coder:6.7b`
- `qwen` / `qwen:7b` / `qwen2`

### Installing Models

```bash
docker exec -it tensoria-ollama ollama pull mistral
docker exec -it tensoria-ollama ollama pull deepseek-coder
docker exec -it tensoria-ollama ollama pull qwen
```

### Authentication

All endpoints except `/health` require the `X-API-Key` header.
    """,
    version="1.0.0",
    # Disable docs in production for security
    docs_url="/docs" if not is_production else None,
    redoc_url="/redoc" if not is_production else None,
    openapi_url="/openapi.json" if not is_production else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(completions.router)
app.include_router(models.router)


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("=" * 60)
    logger.info("🚀 Tensoria API starting...")
    logger.info("DEBUG: Startup event triggered")
    logger.info(f"📍 Ollama URL: {settings.ollama_base_url}")
    logger.info(f"⏱️  Timeout: {settings.ollama_timeout}s")
    logger.info(f"📊 Log level: {settings.log_level}")
    
    if is_production:
        logger.info("🔒 Security: ENABLED (API Key required)")
        logger.info("📖 API Documentation: DISABLED (production mode)")
    else:
        logger.info("⚠️  Security: DISABLED (no API_KEY configured)")
        logger.info("📖 API Documentation: http://localhost:8000/docs")
    
    logger.info("=" * 60)
    logger.info("")
    logger.info("🔍 Health check: http://localhost:8000/health")
    logger.info("")
    logger.info("⚠️  Remember: Models must be installed manually!")
    logger.info("   Example: docker exec -it tensoria-ollama ollama pull mistral")
    logger.info("")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Tensoria API",
        "version": "1.0.0",
        "description": "Open Source LLM API Infrastructure",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "chat": "/v1/chat/completions",
            "completions": "/v1/completions",
            "models": "/v1/models",
        },
    }
