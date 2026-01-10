"""Models listing endpoint - OpenAI-compatible."""

from fastapi import APIRouter, Depends, HTTPException
import logging
import time

from ..models import ModelsListResponse, ModelInfo, ErrorResponse, PullModelRequest, PullModelResponse
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


@router.post(
    "/models/pull",
    response_model=PullModelResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def pull_model(
    request: PullModelRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Pull a model from the Ollama library.
    
    This operation can take a long time (several minutes).
    """
    client = get_ollama_client()
    
    try:
        logger.info(f"Request to pull model: {request.name}")
        await client.pull_model(request.name)
        
        return PullModelResponse(
            status="success",
            message=f"Model '{request.name}' pulled successfully"
        )
        
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": "pull_error",
                }
            },
        )


@router.delete(
    "/models/{model_name:path}",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Model not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def delete_model(
    model_name: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Delete a model from Ollama.
    """
    client = get_ollama_client()
    
    try:
        logger.info(f"Request to delete model: {model_name}")
        await client.delete_model(model_name)
        
        return {
            "status": "success",
            "message": f"Model '{model_name}' deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": "delete_error",
                }
            },
        )
