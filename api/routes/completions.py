"""Text completions endpoint - OpenAI-compatible legacy endpoint."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
import uuid
import json

from ..models import (
    CompletionRequest,
    CompletionResponse,
    CompletionChoice,
    ChatCompletionUsage,
    ErrorResponse,
)
from ..ollama_client import get_ollama_client, ModelNotFoundError, OllamaError
from ..auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["completions"])


@router.post(
    "/completions",
    response_model=CompletionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Model not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def completions(
    request: CompletionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Create a text completion (OpenAI-compatible legacy endpoint).
    
    This endpoint follows the OpenAI Completion API format.
    """
    client = get_ollama_client()
    
    try:
        if request.stream:
            return StreamingResponse(
                stream_completion_response(client, request),
                media_type="text/event-stream",
            )
        
        # Non-streaming response
        result = await client.generate(
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            stream=False,
        )
        
        return CompletionResponse(
            id=f"cmpl-{uuid.uuid4().hex[:24]}",
            model=request.model,
            choices=[
                CompletionChoice(
                    index=0,
                    text=result.get("response", ""),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=result.get("prompt_eval_count", 0),
                completion_tokens=result.get("eval_count", 0),
                total_tokens=result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            ),
        )
        
    except ModelNotFoundError as e:
        logger.warning(f"Model not found: {e.model}")
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": str(e),
                    "type": "model_not_found",
                    "code": "model_not_found",
                }
            },
        )
    except OllamaError as e:
        logger.error(f"Ollama error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": str(e),
                    "type": "server_error",
                    "code": "ollama_error",
                }
            },
        )


async def stream_completion_response(client, request: CompletionRequest):
    """Stream completion response in SSE format."""
    try:
        response_id = f"cmpl-{uuid.uuid4().hex[:24]}"
        
        async for chunk in await client.generate(
            model=request.model,
            prompt=request.prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            stream=True,
        ):
            content = chunk.get("response", "")
            done = chunk.get("done", False)
            
            data = {
                "id": response_id,
                "object": "text_completion",
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "text": content,
                        "finish_reason": "stop" if done else None,
                    }
                ],
            }
            
            yield f"data: {json.dumps(data)}\n\n"
            
            if done:
                yield "data: [DONE]\n\n"
                
    except ModelNotFoundError as e:
        error_data = {
            "error": {
                "message": str(e),
                "type": "model_not_found",
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
    except OllamaError as e:
        error_data = {
            "error": {
                "message": str(e),
                "type": "server_error",
            }
        }
        yield f"data: {json.dumps(error_data)}\n\n"
