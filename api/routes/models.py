"""Models listing endpoint - OpenAI-compatible."""

from fastapi import APIRouter, Depends
import logging
import time

from ..models import ModelsListResponse, ModelInfo, ErrorResponse
from ..ollama_client import get_ollama_client
from ..auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["models"])


@router.get(
    "/models",
    response_model=ModelsListResponse,
    responses={401: {"model": ErrorResponse, "description": "Unauthorized"}},
)
async def list_models(api_key: str = Depends(verify_api_key)):
    """
    List available models (OpenAI-compatible).
    
    Returns only models that are actually installed in Ollama.
    """
    client = get_ollama_client()
    
    try:
        ollama_models = await client.list_models()
        
        models = [
            ModelInfo(
                id=model.get("name", "unknown"),
                created=int(time.time()),  # Ollama doesn't provide creation time
                owned_by="ollama",
            )
            for model in ollama_models
        ]
        
        logger.info(f"📋 Listed {len(models)} installed models")
        
        return ModelsListResponse(data=models)
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return ModelsListResponse(data=[])
