from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import init_db
from app.routes.auth import router as auth_router
from app.routes.pages import router as pages_router
from app.routes.planners import router as planner_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes database schema and application services on startup."""
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# Session middleware for authenticated state tracking
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="pocketsmart_session",
    max_age=14 * 24 * 3600,  # 14 days
    same_site="lax",
    https_only=False,
)

# Cross-origin resource sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include functional routers
app.include_router(auth_router)
app.include_router(pages_router)
app.include_router(planner_router)


@app.get("/startup")
async def startup_check():
    """Health and service initialization status check (Milestone 3.4)."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "sqlite_ready",
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG or True,
    )
