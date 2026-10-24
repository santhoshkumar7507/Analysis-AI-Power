"""Health and readiness API endpoints."""

from datetime import datetime, timezone
import redis
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.database import check_db_connection

router = APIRouter(tags=["Health & Readiness"])


@router.get("/health", status_code=status.HTTP_200_OK)
def liveness_check():
    """Liveness probe to verify that the service is running."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
def readiness_check():
    """Readiness probe checking PostgreSQL database and Redis connectivity."""
    db_ok = check_db_connection()

    # Redis check
    redis_ok = False
    redis_error = None
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=2)
        redis_ok = r.ping()
    except Exception as e:
        redis_error = str(e)

    all_ready = db_ok  # in local dev without redis active, we report status clearly

    response_data = {
        "status": "ready" if all_ready else "degraded",
        "service": settings.PROJECT_NAME,
        "checks": {
            "database": "connected" if db_ok else "unreachable",
            "redis": "connected" if redis_ok else f"disconnected ({redis_error})" if redis_error else "disconnected",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    http_status = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=response_data, status_code=http_status)
