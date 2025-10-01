"""
Configuration management for Cage Pod.

This module provides a centralized configuration system that:
- Loads environment-specific configuration files
- Provides type-safe configuration access
- Supports environment variable overrides
- Validates configuration values
"""

from .config_manager import ConfigManager, get_config
from .settings import Settings

__all__ = ["ConfigManager", "get_config", "Settings"]
