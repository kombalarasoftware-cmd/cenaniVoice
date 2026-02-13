"""
VoiceAI Platform - FastAPI Backend
Main application entry point
"""

from collections import defaultdict
from contextlib import asynccontextmanager
import json as _json

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import time
import uuid

from app.core.config import settings, validate_production_settings
from app.api.v1 import api_router
from app.api.knowledge_base import router as knowledge_base_router
from app.api.prompt_generator import router as prompt_generator_router
from app.api.outbound_calls import router as outbound_calls_router
from app.api.v1.prompt_maker import router as prompt_maker_router
from app.core.database import engine, Base, get_health_status


# =============================================================================
# Structured JSON Logging
# =============================================================================

class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    # Extra keys to promote into the JSON envelope when passed via logger.info(..., extra={})
    _EXTRA_KEYS = (
        "request_id", "method", "path", "status_code",
        "duration_ms", "client_ip", "user_id",
    )

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        for key in self._EXTRA_KEYS:
            value = getattr(record, key, None)
            if value is not None:
                log_data[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            log_data["exception"] = self.formatException(record.exc_info)
        return _json.dumps(log_data)


def _configure_logging() -> None:
    """Set up root logger with JSON formatter for production, human-readable for debug."""
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    handler = logging.StreamHandler()
    if settings.DEBUG:
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    else:
        handler.setFormatter(JSONFormatter())
    root.addHandler(handler)


_configure_logging()
logger = logging.getLogger(__name__)


# =============================================================================
# Security Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class RequestBodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with body larger than the configured limit."""

    def __init__(self, app, max_size_mb: int = 10):
        super().__init__(app)
        self.max_size = max_size_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size is {self.max_size // (1024 * 1024)}MB."},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiter based on client IP.
    Uses a sliding window per minute.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health/ready endpoints
        if request.url.path in ("/health", "/ready"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # Clean old entries and add current request
        hits = self._hits[client_ip]
        self._hits[client_ip] = [t for t in hits if t > window_start]
        self._hits[client_ip].append(now)

        if len(self._hits[client_ip]) > self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)


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

    # Ensure MinIO buckets exist
    try:
        from app.services.minio_service import minio_service
        results = minio_service.ensure_buckets()
        for bucket, created in results.items():
            if created:
                logger.info(f"MinIO bucket created: {bucket}")
            else:
                logger.debug(f"MinIO bucket already exists: {bucket}")
    except Exception as e:
        logger.warning(f"MinIO bucket initialization failed (storage may not work): {e}")

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


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

        # Structured access log (skip noisy health probes)
        if request.url.path not in ("/health", "/ready"):
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2),
                    "client_ip": request.client.host if request.client else "unknown",
                },
            )

        return response


# Security middleware (order matters: outermost middleware runs first)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestBodySizeLimitMiddleware, max_size_mb=settings.MAX_UPLOAD_SIZE_MB)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
)

# Configure CORS with restricted methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-Request-ID",
        "X-Webhook-Secret",
        "X-Webhook-Signature",
    ],
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
app.include_router(prompt_maker_router, prefix="/api/v1")
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
    Does NOT expose internal error types or stack traces to the client.
    """
    request_id = getattr(request.state, "request_id", "unknown")

    # Log full exception with traceback (server-side only)
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {exc} - "
        f"path={request.url.path} method={request.method} request_id={request_id}"
    )

    # Return sanitized error to client - no internal details
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred. Please try again later.",
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
