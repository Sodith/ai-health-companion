"""Root entry point.

Run the API server with:
    python main.py
or directly via uvicorn:
    uvicorn app.main:app --reload
"""

import uvicorn

from app.utils.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.app_debug,
        log_level="debug" if settings.app_debug else "info",
    )
