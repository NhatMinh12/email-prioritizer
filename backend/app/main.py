from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "Email Prioritizer API",
        "version": "0.1.0",
        "environment": settings.environment,
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "database": "not_configured",
        "redis": "not_configured",
    }


# TODO: Import and include routers when created
# from app.api import auth, emails, preferences
# app.include_router(auth.router, prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
# app.include_router(emails.router, prefix=f"{settings.api_v1_prefix}/emails", tags=["emails"])
# app.include_router(preferences.router, prefix=f"{settings.api_v1_prefix}/preferences", tags=["preferences"])