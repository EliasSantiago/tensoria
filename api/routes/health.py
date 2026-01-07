"""Health check endpoint."""

from fastapi import APIRouter
import logging

from ..models import HealthResponse
from ..ollama_client import get_ollama_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of the API and Ollama connection.
    
    Returns:
        - status: "healthy" if Ollama is connected, "unhealthy" otherwise
        - ollama_connected: boolean indicating Ollama connectivity
        - ollama_models_count: number of installed models
    """
    client = get_ollama_client()
    
    is_connected = await client.health_check()
    models_count = 0
    
    if is_connected:
        try:
            models = await client.list_models()
            models_count = len(models)
        except Exception as e:
            logger.warning(f"Error counting models: {e}")
    
    status = "healthy" if is_connected else "unhealthy"
    
    logger.info(f"🏥 Health check: {status} (Ollama connected: {is_connected}, models: {models_count})")
    
    return HealthResponse(
        status=status,
        ollama_connected=is_connected,
        ollama_models_count=models_count,
    )
