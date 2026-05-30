"""Application entry point.

Startup order:
  1. Create FastAPI app with metadata.
  2. Register global exception handlers.
  3. Mount all routers.
  4. Expose /health for load-balancer probes.
"""

from fastapi import FastAPI

from app.controllers.auth_controller import router as auth_router
from app.controllers.prescription_controller import router as prescription_router
from app.middleware.auth_middleware import JWTAuthMiddleware
from app.middleware.exception_middleware import register_exception_handlers
from app.utils.config import get_settings
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Production-ready AI Health Companion backend API.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- Global exception handlers -------------------------------------------
register_exception_handlers(app)

# --- Middleware --------------------------------------------------------------
app.add_middleware(JWTAuthMiddleware)

# --- Routers -----------------------------------------------------------------
app.include_router(auth_router, prefix="/api/v1")
app.include_router(prescription_router, prefix="/api/v1")

# --- System endpoints --------------------------------------------------------

@app.get("/health", tags=["system"], include_in_schema=False)
def health_check() -> dict[str, str]:
    """Liveness probe — used by load balancers and container orchestrators."""
    return {"status": "ok"}


logger.info("AI Health Companion API started | env=%s", settings.app_env)
