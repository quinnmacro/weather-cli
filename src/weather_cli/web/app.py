"""
FastAPI Web Application for Weather CLI
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# Base directory for templates and static files
BASE_DIR = Path(__file__).parent

# Templates instance (initialized at module load)
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    app = FastAPI(
        title="Weather CLI Pro",
        description="CalTopo-style route weather planning",
        version="0.1.0",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files
    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Include routers
    from .routes import routes as routes_router
    from .routes import upload as upload_router
    from .routes import weather as weather_router

    app.include_router(routes_router.router, tags=["pages"])
    app.include_router(upload_router.router, prefix="/api", tags=["upload"])
    app.include_router(weather_router.router, prefix="/api/weather", tags=["weather"])

    return app


# Create app instance
app = create_app()


def cli():
    """CLI entry point for running the web server"""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)


if __name__ == "__main__":
    cli()
