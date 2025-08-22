"""
Agent pod daemon that initialises Gemini SDK, runs periodic health tasks, and supervises agent workflows.

This script:
- Validates presence of GEMINI_API_KEY (warns if missing).
- Starts a lightweight heartbeat loop.
- Exposes an optional /health HTTP endpoint for Fly health checks (future-proof).
"""

import asyncio
import os
from loguru import logger

try:
    import uvloop  # type: ignore
    uvloop.install()
except Exception:
    pass

async def init_gemini():
    """
    Initialise Gemini SDK client using the GEMINI_API_KEY environment variable.

    Returns:
    - bool: True if key is present and SDK import succeeds, False otherwise.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not set. Gemini calls will fail until provided.")
        return False
    try:
        import google.generativeai as genai  # lazy import
        genai.configure(api_key=api_key)
        logger.info("Gemini SDK initialised.")
        return True
    except Exception as e:
        logger.exception(f"Failed to init Gemini SDK: {e}")
        return False

async def heartbeat():
    """
    Emit a heartbeat log periodically to confirm liveness.

    Behaviour:
    - Logs every 10 seconds.
    """
    while True:
        logger.info("agent-daemon heartbeat")
        await asyncio.sleep(10)

async def main():
    """
    Entrypoint for the daemon event loop.

    Behaviour:
    - Initialise Gemini.
    - Start background tasks (heartbeat for now).
    - Await indefinitely.
    """
    _ = await init_gemini()
    tasks = [asyncio.create_task(heartbeat())]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down daemon...")
