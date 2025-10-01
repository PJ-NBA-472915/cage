"""
CrewAI Service Main Application

FastAPI application for managing AI agents and crews.
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Configure JSONL logging
from src.cage.utils.jsonl_logger import setup_jsonl_logger
from src.cage.utils.problem_details import setup_problem_detail_handlers
from src.crew_service.middleware_request_id import RequestIDMiddleware
from src.crew_service.router import router as crew_router

logger = setup_jsonl_logger("crewai", level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting CrewAI service")
    yield
    logger.info("Shutting down CrewAI service")


# Create FastAPI app
app = FastAPI(
    title="CrewAI Service",
    description="AI agents and crews for automated development tasks",
    version="1.0.0",
    lifespan=lifespan,
)

# Add request ID middleware (must be first)
app.add_middleware(RequestIDMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Problem Details exception handlers
setup_problem_detail_handlers(app)

# Mount the crew router
app.include_router(crew_router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "CrewAI Service", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
