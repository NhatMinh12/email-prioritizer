import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth, emails, preferences
from app.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Email Prioritizer API",
    description="Smart email prioritization using Claude AI",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(
    emails.router,
    prefix=f"{settings.api_v1_prefix}/emails",
    tags=["emails"],
)
app.include_router(
    preferences.router,
    prefix=f"{settings.api_v1_prefix}/preferences",
    tags=["preferences"],
)


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Email Prioritizer API",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health")
def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
    }


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions."""
    logger.error("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
