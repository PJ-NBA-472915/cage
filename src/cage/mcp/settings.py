"""
MCP Server Settings

Environment variable configuration for the Cage MCP server.
"""

import os


class MCPSettings:
    """Settings for the Cage MCP server."""

    def __init__(self) -> None:
        # API configuration
        self.api_base_url: str = os.getenv("API_BASE_URL", "http://api:8000")
        self.pod_token: str = os.getenv("POD_TOKEN", "test-mcp-token")
        self.api_timeout_s: int = int(os.getenv("API_TIMEOUT_S", "30"))

        # MCP server configuration
        self.host: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("MCP_PORT", "8765"))

        # Logging configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.service_name: str = "cage-mcp"


# Global settings instance
settings = MCPSettings()
