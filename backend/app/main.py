"""Application entry point.

Startup order:
  1. Create FastAPI app with metadata.
  2. Register global exception handlers.
  3. Mount all routers.
  4. Expose /health for load-balancer probes.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.auth_controller import router as auth_router
from app.controllers.prescription_controller import router as prescription_router
from app.controllers.analysis_controller import router as analysis_router
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

# ── Middleware order note ────────────────────────────────────────────────────
# FastAPI/Starlette applies middleware in LIFO order (last added = first run).
# CORS must run FIRST (before JWT) so that OPTIONS preflight requests are
# answered with the correct headers and never reach the auth check.
# Therefore: add JWTAuthMiddleware first, CORSMiddleware second.
# ─────────────────────────────────────────────────────────────────────────────

# --- Auth Middleware (added first → runs SECOND) ----------------------------
app.add_middleware(JWTAuthMiddleware)

# --- CORS Middleware (added last → runs FIRST) ------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Routers -----------------------------------------------------------------
app.include_router(auth_router, prefix="/api/v1")
app.include_router(prescription_router, prefix="/api/v1")
app.include_router(analysis_router, prefix="/api/v1")

# --- System endpoints --------------------------------------------------------

@app.get("/health", tags=["system"], include_in_schema=False)
def health_check() -> dict[str, str]:
    """Liveness probe — used by load balancers and container orchestrators."""
    return {"status": "ok"}


logger.info("AI Health Companion API started | env=%s", settings.app_env)
