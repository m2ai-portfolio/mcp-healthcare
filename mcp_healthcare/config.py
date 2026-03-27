"""Configuration management using Pydantic settings."""

import os
from pathlib import Path
from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    mcp_data_dir: str = Field(
        default="./data",
        description="Directory for SQLite and data files"
    )
    mcp_db_name: str = Field(
        default="mcp_hc.sqlite",
        description="SQLite filename, relative to MCP_DATA_DIR"
    )
    mcp_log_level: str = Field(
        default="INFO",
        description="Logging verbosity"
    )
    mcp_audit_enable: bool = Field(
        default=True,
        description="Toggle HIPAA audit logging"
    )

    @property
    def data_dir_path(self) -> Path:
        """Get the data directory as a Path object."""
        return Path(self.mcp_data_dir).resolve()

    @property
    def db_path(self) -> Path:
        """Get the full database path."""
        return self.data_dir_path / self.mcp_db_name

    def ensure_data_dir(self) -> None:
        """Create the data directory if it doesn't exist."""
        self.data_dir_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
