"""
VoiceAI Platform - FastAPI Backend
Main application entry point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import time
import uuid

from app.core.config import settings, validate_production_settings
from app.api.v1 import api_router
from app.api.knowledge_base import router as knowledge_base_router
from app.api.prompt_generator import router as prompt_generator_router
from app.api.outbound_calls import router as outbound_calls_router
from app.core.database import engine, Base, get_health_status

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    logger.info(f"Starting VoiceAI Platform v{settings.VERSION}")

    # Validate production settings
    if not settings.DEBUG:
        if not validate_production_settings():
            logger.warning("Production settings validation failed - some features may not work")

    # Create database tables (in production, use Alembic migrations)
    Base.metadata.create_all(bind=engine)

    yield

    # Shutdown
    logger.info("Shutting down VoiceAI Platform")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered voice agent platform with OpenAI Realtime API",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# Request ID middleware for tracing
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracing"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for container orchestration"""
    return JSONResponse(
        content={
            "status": "healthy",
            "version": settings.VERSION,
            "app": settings.APP_NAME,
        }
    )


# Ready check endpoint with actual connectivity tests
@app.get("/ready", tags=["Health"])
async def ready_check():
    """
    Readiness check endpoint.
    Actually tests database and Redis connectivity.
    """
    health = get_health_status()

    status_code = 200 if health["healthy"] else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if health["healthy"] else "not_ready",
            "database": health["database"],
            "redis": health["redis"],
        }
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")
app.include_router(knowledge_base_router, prefix="/api/v1")
app.include_router(prompt_generator_router, prefix="/api/v1")
app.include_router(outbound_calls_router, prefix="/api/v1")


# HTTP Exception handler - let FastAPI handle these properly
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with proper status codes"""
    request_id = getattr(request.state, "request_id", "unknown")

    # Log 4xx as warning, 5xx as error
    if exc.status_code >= 500:
        logger.error(
            f"HTTP {exc.status_code}: {exc.detail} - "
            f"path={request.url.path} method={request.method} request_id={request_id}"
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"HTTP {exc.status_code}: {exc.detail} - "
            f"path={request.url.path} method={request.method} request_id={request_id}"
        )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
        },
    )


# Global exception handler for unexpected errors only
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unexpected errors.
    Only catches non-HTTP exceptions.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log full exception with traceback
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {exc} - "
        f"path={request.url.path} method={request.method} request_id={request_id}"
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error_type": type(exc).__name__,
            "request_id": request_id,
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
