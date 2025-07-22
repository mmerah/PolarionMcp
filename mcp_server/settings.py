from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PolarionSettings(BaseSettings):
    """
    Manages Polarion connection settings, loaded from a .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    polarion_url: str = Field(..., alias="POLARION_URL")
    polarion_user: str = Field(..., alias="POLARION_USER")
    polarion_token: str = Field(..., alias="POLARION_TOKEN")


# Create a single, reusable instance of the settings
settings = PolarionSettings()  # type: ignore[call-arg]
