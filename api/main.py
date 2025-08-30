"""
Zeno FastAPI Application

Main FastAPI application providing REST API endpoints for iOS app integration
and external services interaction.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import get_settings
from api.middleware.auth import setup_auth_middleware
from api.routes import auth, tasks, calendar, briefings, agent, agent_session, integrations, ios, clerk_webhooks, user

# Initialize settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title=f"{settings.app_name} API",
    description="Daily Planning AI Assistant API",
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Configure CORS
# Allow localhost origins for frontend development and ngrok for iOS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Allow ngrok domains for iOS app
        "https://*.ngrok-free.app",
        "https://d95f3ba12854.ngrok-free.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "Authorization"],
)

# Setup authentication middleware
setup_auth_middleware(app)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
app.include_router(briefings.router, prefix="/briefings", tags=["Briefings"])
app.include_router(agent.router, prefix="/agent", tags=["Agent"])
app.include_router(agent_session.router, prefix="/agent/session", tags=["Agent Sessions"])
app.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
app.include_router(ios.router, prefix="/ios", tags=["iOS"])
app.include_router(clerk_webhooks.router, prefix="/webhooks/clerk", tags=["Clerk Webhooks"])


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "version": settings.version,
        "environment": settings.environment,
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.version
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions."""
    if settings.debug:
        import traceback
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "traceback": traceback.format_exc(),
                "status_code": 500
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "status_code": 500
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.api_workers
    )
