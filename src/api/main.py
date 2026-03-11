"""Main FastAPI application entry point.

This module initializes the FastAPI app and provides basic endpoints for
status monitoring and health checks. Additional routers are mounted in the
routes/ directory for API functionality.
"""

from fastapi import FastAPI
import logging
from typing import Dict

app = FastAPI(
    title="Disaster Management API",
    description="API for disaster response and resource allocation using AI",
    version="0.1.0"
)


@app.get("/", response_model=Dict[str, str])
async def root() -> Dict[str, str]:
    """Simple root endpoint for quick status checks.

    Returns
    -------
    Dict[str, str]
        A dictionary with a single 'status' key set to 'ok'.
    """
    logging.debug("root endpoint called")
    return {"status": "ok"}


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """Health check endpoint for deployment automation.

    Returns
    -------
    Dict[str, str]
        A dictionary with 'health' = 'green'.
    """
    logging.debug("health check invoked")
    return {"health": "green"}
