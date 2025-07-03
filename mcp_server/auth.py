"""
Authentication for the MCP Server API.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from .config import settings

API_KEY_HEADER = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="The API Key for accessing the MCP Server.",
)


def get_api_key(api_key: str = Depends(API_KEY_HEADER)) -> str:
    """
    Dependency to validate the API key.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key is missing",
        )
    if api_key != settings.MCP_SERVER_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return api_key
