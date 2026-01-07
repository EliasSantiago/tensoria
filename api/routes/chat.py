"""Chat completions endpoint - OpenAI-compatible."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
import uuid
import json

from ..models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatCompletionUsage,
    ChatMessage,
    ErrorResponse,
    ErrorDetail,
)
from ..ollama_client import get_ollama_client, ModelNotFoundError, OllamaError
from ..auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Model not found"},
        500: {"model": ErrorResponse, "description": "Server error"},
    },
)
async def chat_completions(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key),
):
    """
    Create a chat completion (OpenAI-compatible).
    
    This endpoint follows the OpenAI Chat Completion API format.
    """
    client = get_ollama_client()
    
    # Convert messages to Ollama format
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    
    try:
        if request.stream:
            return StreamingResponse(
                stream_chat_response(client, request, messages),
                media_type="text/event-stream",
            )
        
        # Non-streaming response
        result = await client.chat(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            stream=False,
        )
        
        # Convert Ollama response to OpenAI format
        response_message = result.get("message", {})
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:24]}",
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role=response_message.get("role", "assistant"),
                        content=response_message.get("content", ""),
                    ),
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


async def stream_chat_response(client, request: ChatCompletionRequest, messages: list):
    """Stream chat response in SSE format."""
    try:
        response_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
        
        async for chunk in await client.chat(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            stream=True,
        ):
            content = chunk.get("message", {}).get("content", "")
            done = chunk.get("done", False)
            
            data = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": content} if content else {},
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
