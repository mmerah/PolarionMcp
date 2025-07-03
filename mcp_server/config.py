"""
Configuration for the MCP Server.
Loads settings from environment variables and .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):  # type: ignore[misc]
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields in .env file
    )

    # API Key to secure the server's own endpoints
    MCP_SERVER_API_KEY: str

    # Server configuration
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8443

    # SSL configuration
    SSL_KEYFILE: str = "mcp_server/certs/key.pem"
    SSL_CERTFILE: str = "mcp_server/certs/cert.pem"

    # Logging configuration
    LOG_LEVEL: str = "INFO"

    # Polarion configuration (required, used by PolarionDriver)
    POLARION_USER: str
    POLARION_TOKEN: str
    POLARION_URL: str


settings = Settings()
