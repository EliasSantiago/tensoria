"""HTTP client for communicating with Ollama."""

import httpx
import logging
from typing import Optional, AsyncGenerator
import json

from .config import get_settings

logger = logging.getLogger(__name__)


class OllamaError(Exception):
    """Base exception for Ollama errors."""
    pass


class ModelNotFoundError(OllamaError):
    """Raised when the requested model is not installed."""
    def __init__(self, model: str):
        self.model = model
        super().__init__(f"Model '{model}' is not installed. Install it with: docker exec -it tensoria-ollama ollama pull {model}")


class OllamaConnectionError(OllamaError):
    """Raised when unable to connect to Ollama."""
    pass


class OllamaClient:
    """Async HTTP client for Ollama API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        settings = get_settings()
        self.base_url = base_url or settings.ollama_base_url
        self.timeout = timeout or settings.ollama_timeout
        
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[dict] = None,
        stream: bool = False
    ) -> dict | AsyncGenerator[dict, None]:
        """Make an HTTP request to Ollama."""
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if stream:
                    return self._stream_request(client, method, url, json_data)
                
                response = await client.request(method, url, json=json_data)
                
                if response.status_code == 404:
                    model = json_data.get("model", "unknown") if json_data else "unknown"
                    raise ModelNotFoundError(model)
                
                response.raise_for_status()
                return response.json()
                
        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to Ollama at {self.base_url}: {e}")
            raise OllamaConnectionError(f"Cannot connect to Ollama at {self.base_url}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout connecting to Ollama: {e}")
            raise OllamaError(f"Timeout waiting for Ollama response")
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Ollama: {e}")
            raise OllamaError(f"Ollama error: {e.response.text}")
    
    async def _stream_request(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        json_data: Optional[dict]
    ) -> AsyncGenerator[dict, None]:
        """Stream response from Ollama."""
        async with client.stream(method, url, json=json_data) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)
    
    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            logger.info(f"DEBUG: Checking Ollama health at {self.base_url}...")
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                logger.info(f"DEBUG: Ollama health response: {response.status_code}")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> list[dict]:
        """List all installed models."""
        try:
            result = await self._request("GET", "/api/tags")
            return result.get("models", [])
        except OllamaConnectionError:
            return []
    
    async def chat(
        self,
        model: str,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stop: Optional[list[str]] = None,
        stream: bool = False
    ) -> dict | AsyncGenerator[dict, None]:
        """Send a chat completion request to Ollama."""
        
        # First check if model exists
        models = await self.list_models()
        model_names = [m.get("name", "").split(":")[0] for m in models]
        model_base = model.split(":")[0]
        
        if model_base not in model_names and model not in [m.get("name") for m in models]:
            raise ModelNotFoundError(model)
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        if stop:
            payload["options"]["stop"] = stop
        
        logger.info(f"🤖 Chat request to model: {model}")
        
        result = await self._request("POST", "/api/chat", payload, stream=stream)
        return result
    
    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stop: Optional[list[str]] = None,
        stream: bool = False
    ) -> dict | AsyncGenerator[dict, None]:
        """Send a completion request to Ollama."""
        
        # First check if model exists
        models = await self.list_models()
        model_names = [m.get("name", "").split(":")[0] for m in models]
        model_base = model.split(":")[0]
        
        if model_base not in model_names and model not in [m.get("name") for m in models]:
            raise ModelNotFoundError(model)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
            }
        }
        
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        
        if stop:
            payload["options"]["stop"] = stop
        
        logger.info(f"📝 Generate request to model: {model}")
        
        result = await self._request("POST", "/api/generate", payload, stream=stream)
        return result
    
    async def pull_model(self, model: str) -> dict:
        """
        Pull a model from the Ollama library.
        
        Args:
            model: The name of the model to pull (e.g., "mistral")
            
        Returns:
            The final response from Ollama.
        """
        logger.info(f"⬇️ Pulling model: {model}")
        
        # We use stream=False to wait for the full download (can take a while)
        # For a better UX in the future, we should implement streaming
        payload = {
            "name": model,
            "stream": False
        }
        
        try:
            # Increase timeout specifically for pull operations as they can take a long time
            async with httpx.AsyncClient(timeout=1200.0) as client: # 20 minutes timeout
                response = await client.post(f"{self.base_url}/api/pull", json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.TimeoutException:
            logger.error(f"Timeout pulling model {model}")
            raise OllamaError(f"Timeout pulling model {model}")
        except Exception as e:
            logger.error(f"Error pulling model {model}: {e}")
            raise OllamaError(f"Error pulling model: {str(e)}")

    async def delete_model(self, model: str) -> bool:
        """
        Delete a model from Ollama.
        
        Args:
            model: The name of the model to delete
            
        Returns:
            True if successful
        """
        logger.info(f"🗑️ Deleting model: {model}")
        
        payload = {"name": model}
        
        try:
            await self._request("DELETE", "/api/delete", payload)
            return True
        except Exception as e:
            logger.error(f"Error deleting model {model}: {e}")
            raise OllamaError(f"Error deleting model: {str(e)}")


# Singleton client instance
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get the singleton Ollama client instance."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
