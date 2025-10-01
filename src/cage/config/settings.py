"""
Pydantic settings model for Cage Pod configuration.

This module defines the configuration schema using Pydantic for validation
and type safety.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseSettings, Field, validator


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    url: str = Field(..., description="Database connection URL")
    port: int = Field(default=5432, description="Database port")
    host: str = Field(default="postgres", description="Database host")
    name: str = Field(default="cage", description="Database name")
    user: str = Field(default="postgres", description="Database user")
    password: str = Field(default="password", description="Database password")

    class Config:
        env_prefix = "DB_"


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    url: str = Field(default="redis://redis:6379", description="Redis connection URL")
    host: str = Field(default="redis", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: str | None = Field(default=None, description="Redis password")

    class Config:
        env_prefix = "REDIS_"


class APISettings(BaseSettings):
    """API configuration settings."""

    base_url: str = Field(default="http://api:8000", description="API base URL")
    reload: bool = Field(default=False, description="Enable auto-reload in development")
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")

    class Config:
        env_prefix = "API_"


class MCPSettings(BaseSettings):
    """MCP server configuration settings."""

    port: int = Field(default=8765, description="MCP server port")
    tokens: str = Field(
        default="test-mcp-token", description="MCP authentication tokens"
    )
    session_ttl: int = Field(
        default=3600, description="Session time-to-live in seconds"
    )
    rate_max_calls: int = Field(
        default=240, description="Maximum calls per rate limit window"
    )

    class Config:
        env_prefix = "MCP_"


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="text", description="Log format (text or json)")
    file_path: str | None = Field(default=None, description="Log file path")
    max_size: int = Field(
        default=10485760, description="Maximum log file size in bytes"
    )
    backup_count: int = Field(default=5, description="Number of backup files to keep")

    class Config:
        env_prefix = "LOG_"

    @validator("level")  # type: ignore[misc]
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("format")  # type: ignore[misc]
    def validate_log_format(cls, v: str) -> str:
        valid_formats = ["text", "json"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}")
        return v.lower()


class AgentSettings(BaseSettings):
    """Agent configuration settings."""

    role: str = Field(..., description="Agent role")
    goal: str = Field(..., description="Agent goal")
    backstory: str = Field(..., description="Agent backstory")
    verbose: bool = Field(default=True, description="Enable verbose output")
    allow_delegation: bool = Field(default=False, description="Allow task delegation")
    memory: bool = Field(default=False, description="Enable memory")
    max_iter: int | None = Field(default=None, description="Maximum iterations")
    max_execution_time: int | None = Field(
        default=None, description="Maximum execution time in seconds"
    )
    max_rpm: int | None = Field(default=None, description="Maximum requests per minute")
    max_prompt_tokens: int | None = Field(
        default=None, description="Maximum prompt tokens"
    )
    max_completion_tokens: int | None = Field(
        default=None, description="Maximum completion tokens"
    )
    temperature: float | None = Field(
        default=None, description="Temperature for text generation"
    )
    top_p: float | None = Field(default=None, description="Top-p for text generation")
    frequency_penalty: float | None = Field(
        default=None, description="Frequency penalty"
    )
    presence_penalty: float | None = Field(default=None, description="Presence penalty")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        env_prefix = ""


class Settings(BaseSettings):
    """Main application settings."""

    # Core settings
    pod_token: str = Field(..., description="Pod authentication token")
    repo_path: str = Field(..., description="Repository path for file operations")
    environment: str = Field(default="development", description="Environment name")

    # Service settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    api: APISettings = Field(default_factory=APISettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    # External services
    openai_api_key: str | None = Field(default=None, description="OpenAI API key")

    # Development settings
    dev_mode: bool = Field(default=False, description="Development mode")
    test_mode: bool = Field(default=False, description="Test mode")

    # Debugging settings
    debugpy_enabled: bool = Field(default=False, description="Enable debugpy")
    debugpy_wait_for_client: bool = Field(
        default=False, description="Wait for debugpy client"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("environment")  # type: ignore[misc]
    def validate_environment(cls, v: str) -> str:
        valid_environments = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_environments:
            raise ValueError(f"Environment must be one of {valid_environments}")
        return v.lower()

    @validator("repo_path")  # type: ignore[misc]
    def validate_repo_path(cls, v: str | Path) -> str | Path:
        if not Path(v).exists():
            raise ValueError(f"Repository path does not exist: {v}")
        return v

    def get_agent_config(self, agent_name: str) -> AgentSettings:
        """Get configuration for a specific agent."""
        # This would be implemented to load agent-specific settings
        # For now, return a default configuration
        return AgentSettings(
            role=f"{agent_name.title()} Agent",
            goal=f"Execute {agent_name} tasks",
            backstory=f"You are a {agent_name} agent",
        )
