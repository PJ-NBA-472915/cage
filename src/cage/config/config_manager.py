"""
Configuration manager for Cage Pod.

This module provides a centralized way to manage configuration across different
environments and services.
"""

import os
from pathlib import Path
from typing import Any

from .settings import Settings


class ConfigManager:
    """Manages configuration loading and access."""

    def __init__(self, environment: str | None = None):
        """Initialize the configuration manager.

        Args:
            environment: Environment name (development, testing, production)
                        If None, will be determined from ENVIRONMENT env var
        """
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self._settings: Settings | None = None
        self._config_dir = Path(__file__).parent.parent.parent.parent / "config"

    def load_config(self) -> Settings:
        """Load configuration for the current environment.

        Returns:
            Settings object with loaded configuration

        Raises:
            FileNotFoundError: If environment config file not found
            ValueError: If configuration validation fails
        """
        if self._settings is not None:
            return self._settings

        # Determine config file path
        config_file = self._get_config_file_path()

        # Load environment-specific config if it exists
        if config_file.exists():
            os.environ["ENV_FILE"] = str(config_file)

        # Load settings
        self._settings = Settings()

        return self._settings

    def get_config(self) -> Settings:
        """Get the current configuration.

        Returns:
            Settings object with current configuration
        """
        if self._settings is None:
            return self.load_config()
        return self._settings

    def reload_config(self) -> Settings:
        """Reload configuration from files.

        Returns:
            Settings object with reloaded configuration
        """
        self._settings = None
        return self.load_config()

    def get_agent_config(self, agent_name: str) -> dict[str, Any]:
        """Get configuration for a specific agent.

        Args:
            agent_name: Name of the agent (e.g., 'planner', 'implementer')

        Returns:
            Dictionary with agent configuration
        """
        settings = self.get_config()
        agent_settings = settings.get_agent_config(agent_name)

        # Convert to dictionary for easier access
        return agent_settings.dict()  # type: ignore[no-any-return]

    def get_database_url(self) -> str:
        """Get the database URL.

        Returns:
            Database connection URL
        """
        settings = self.get_config()
        return settings.database.url

    def get_redis_url(self) -> str:
        """Get the Redis URL.

        Returns:
            Redis connection URL
        """
        settings = self.get_config()
        return settings.redis.url

    def get_api_base_url(self) -> str:
        """Get the API base URL.

        Returns:
            API base URL
        """
        settings = self.get_config()
        return settings.api.base_url

    def get_mcp_config(self) -> dict[str, Any]:
        """Get MCP server configuration.

        Returns:
            Dictionary with MCP configuration
        """
        settings = self.get_config()
        return settings.mcp.dict()  # type: ignore[no-any-return]

    def get_logging_config(self) -> dict[str, Any]:
        """Get logging configuration.

        Returns:
            Dictionary with logging configuration
        """
        settings = self.get_config()
        return settings.logging.dict()  # type: ignore[no-any-return]

    def is_development(self) -> bool:
        """Check if running in development mode.

        Returns:
            True if in development mode
        """
        settings = self.get_config()
        return settings.dev_mode or self.environment == "development"

    def is_testing(self) -> bool:
        """Check if running in testing mode.

        Returns:
            True if in testing mode
        """
        settings = self.get_config()
        return settings.test_mode or self.environment == "testing"

    def is_production(self) -> bool:
        """Check if running in production mode.

        Returns:
            True if in production mode
        """
        return self.environment == "production"

    def _get_config_file_path(self) -> Path:
        """Get the path to the environment-specific config file.

        Returns:
            Path to the config file
        """
        config_file_name = f"{self.environment}.env"
        return self._config_dir / config_file_name

    def validate_config(self) -> bool:
        """Validate the current configuration.

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        try:
            self.load_config()
            return True
        except Exception as e:
            raise ValueError(f"Configuration validation failed: {e}") from e


# Global configuration manager instance
_config_manager: ConfigManager | None = None


def get_config_manager(environment: str | None = None) -> ConfigManager:
    """Get the global configuration manager instance.

    Args:
        environment: Environment name (optional)

    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None or (
        environment and _config_manager.environment != environment
    ):
        _config_manager = ConfigManager(environment)
    return _config_manager


def get_config(environment: str | None = None) -> Settings:
    """Get configuration for the specified environment.

    Args:
        environment: Environment name (optional)

    Returns:
        Settings object with configuration
    """
    manager = get_config_manager(environment)
    return manager.get_config()


def reload_config(environment: str | None = None) -> Settings:
    """Reload configuration for the specified environment.

    Args:
        environment: Environment name (optional)

    Returns:
        Settings object with reloaded configuration
    """
    manager = get_config_manager(environment)
    return manager.reload_config()
