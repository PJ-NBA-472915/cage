"""
Crew API Service

FastAPI application for CrewAI service endpoints.
"""

import logging
import os
import sys
from datetime import datetime, timezone

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Debugpy integration for container debugging
if os.getenv("DEBUGPY_ENABLED", "0") == "1":
    import debugpy

    try:
        debugpy.listen(("0.0.0.0", 5678))
        if os.getenv("DEBUGPY_WAIT_FOR_CLIENT", "0") == "1":
            debugpy.wait_for_client()
        print("Debugpy enabled - waiting for debugger to attach on port 5678")
    except RuntimeError as e:
        if "Address already in use" in str(e):
            print("Debugpy port 5678 already in use, skipping debugpy setup")
        else:
            raise

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import crew service components
from src.cage.utils.jsonl_logger import setup_jsonl_logger
from src.cage.utils.problem_details import setup_problem_detail_handlers
from src.cage.utils.request_id_middleware import EnhancedRequestIDMiddleware
from src.crew_service.router import router as crew_router

# Create FastAPI application
app = FastAPI(
    title="Crew API Service",
    description="CrewAI service for managing AI agents, crews, and task execution",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure JSONL logging
logger = setup_jsonl_logger("crew-api", level=logging.INFO)

# Add middleware
app.add_middleware(EnhancedRequestIDMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup problem detail handlers
setup_problem_detail_handlers(app)

# Mount crew router
app.include_router(crew_router)


# Application lifespan
@app.on_event("startup")
async def startup_event():
    """Initialize service on startup."""
    logger.info("Crew API service starting up")

    # Log environment info
    pod_id = os.getenv("POD_ID", "dev-pod")
    environment = os.getenv("ENVIRONMENT", "development")
    dev_mode = os.getenv("DEV_MODE", "false")

    logger.info(
        "Service initialized",
        extra={
            "pod_id": pod_id,
            "environment": environment,
            "dev_mode": dev_mode,
            "startup_time": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Crew API service shutting down")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Crew API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8004, log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
