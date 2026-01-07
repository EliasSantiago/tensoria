"""Authentication middleware for Tensoria API.

Provides API Key authentication to restrict access to authorized clients only.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional
import logging
import secrets

from .config import get_settings

logger = logging.getLogger(__name__)

# API Key header definition
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API Key for authentication. Required for all endpoints except /health."
)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verify the API key from the request header.
    
    Args:
        api_key: The API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    settings = get_settings()
    
    # If no API key is configured, allow all requests (development mode)
    if not settings.api_key:
        logger.warning("⚠️  No API_KEY configured - running in INSECURE mode!")
        return "no-key-configured"
    
    # Check if API key was provided
    if not api_key:
        logger.warning("🚫 Request rejected: No API key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "API key is required",
                    "type": "authentication_error",
                    "code": "missing_api_key"
                }
            }
        )
    
    # Validate API key using constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(api_key, settings.api_key):
        logger.warning(f"🚫 Request rejected: Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": "Invalid API key",
                    "type": "authentication_error",
                    "code": "invalid_api_key"
                }
            }
        )
    
    return api_key


def generate_api_key(length: int = 48) -> str:
    """
    Generate a secure random API key.
    
    Args:
        length: Length of the API key (default: 48 characters)
        
    Returns:
        A secure random API key string
    """
    return secrets.token_urlsafe(length)


# For convenience, expose a function to generate a new key
if __name__ == "__main__":
    print(f"Generated API Key: tensoria_{generate_api_key()}")
