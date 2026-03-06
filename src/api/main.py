# FastAPI app entry point
from fastapi import FastAPI
import logging

app = FastAPI()

@app.get('/')
async def root():
    # simple root endpoint for quick checks
    logging.debug("root endpoint called")
    return {'status': 'ok'}


@app.get('/health')
async def health_check():
    """Additional health check endpoint for automation.
    """
    logging.debug("health check invoked")
    return {'health': 'green'}
