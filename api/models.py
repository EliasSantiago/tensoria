"""Pydantic models for OpenAI-compatible API requests and responses."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import time


# =============================================================================
# Chat Completion Models (OpenAI-compatible)
# =============================================================================

class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    """Request body for chat completions."""
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    stream: Optional[bool] = False
    stop: Optional[list[str]] = None


class ChatCompletionChoice(BaseModel):
    """A single choice in a chat completion response."""
    index: int
    message: ChatMessage
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response body for chat completions."""
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[ChatCompletionChoice]
    usage: ChatCompletionUsage


# =============================================================================
# Completion Models (Legacy)
# =============================================================================

class CompletionRequest(BaseModel):
    """Request body for text completions."""
    model: str
    prompt: str
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    stream: Optional[bool] = False
    stop: Optional[list[str]] = None


class CompletionChoice(BaseModel):
    """A single choice in a completion response."""
    index: int
    text: str
    finish_reason: str


class CompletionResponse(BaseModel):
    """Response body for text completions."""
    id: str
    object: Literal["text_completion"] = "text_completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: list[CompletionChoice]
    usage: ChatCompletionUsage


# =============================================================================
# Models List
# =============================================================================

class ModelInfo(BaseModel):
    """Information about a single model."""
    id: str
    object: Literal["model"] = "model"
    created: int
    owned_by: str = "ollama"


class ModelsListResponse(BaseModel):
    """Response body for listing models."""
    object: Literal["list"] = "list"
    data: list[ModelInfo]


class PullModelRequest(BaseModel):
    """Request body for pulling a model."""
    name: str


class PullModelResponse(BaseModel):
    """Response body for pulling a model."""
    status: str
    message: str


# =============================================================================
# Health Check
# =============================================================================

class HealthResponse(BaseModel):
    """Response body for health check."""
    status: Literal["healthy", "unhealthy"]
    ollama_connected: bool
    ollama_models_count: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# =============================================================================
# Error Models
# =============================================================================

class ErrorDetail(BaseModel):
    """Error detail information."""
    message: str
    type: str
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
