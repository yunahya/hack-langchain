"""
FastAPI application entry point for LangGraph workflow APIs.

Provides REST API endpoints for:
- HTML Page Modifier: POST /api/v1/html-modifier
- Report Generator: POST /api/v1/report-generator
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import html_modifier_router, report_generator_router


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup: Load environment variables
    load_dotenv()
    logger.info("LangGraph Workflows API starting...")
    logger.info(f"CORS origins: {settings.cors_origins}")

    yield

    # Shutdown
    logger.info("LangGraph Workflows API shutting down...")


app = FastAPI(
    title="LangGraph Workflows API",
    description="""
REST API for LangGraph-based business report workflows.

## Endpoints

### HTML Page Modifier
- **POST /api/v1/html-modifier**: Modify HTML pages using AI based on natural language requests.

### Report Generator
- **POST /api/v1/report-generator**: Generate Korean business reports with AI-powered content creation.

## Features
- Supports Google Gemini, Azure OpenAI, and OpenAI models
- Configurable LLM parameters per request
- Parallel page generation for faster report creation
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(
    html_modifier_router,
    prefix="/api/v1",
    tags=["HTML Modifier"],
)
app.include_router(
    report_generator_router,
    prefix="/api/v1",
    tags=["Report Generator"],
)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirects to docs."""
    return {
        "message": "LangGraph Workflows API",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
