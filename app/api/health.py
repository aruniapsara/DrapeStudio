"""Health check and metrics endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

router = APIRouter(tags=["health"])

# Record startup time for uptime calculation
_START_TIME = time.time()


def _get_uptime_seconds() -> int:
    return int(time.time() - _START_TIME)


@router.get("/health")
async def health_check():
    """Basic liveness probe."""
    return {"status": "ok", "version": settings.APP_VERSION}


@router.get("/health/detailed")
async def detailed_health(db: Session = Depends(get_db)):
    """Readiness probe: checks database, Redis, and external API config."""
    checks: dict[str, str] = {}

    # Database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Redis
    try:
        import redis as _redis
        r = _redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    # Google Gemini API key
    checks["gemini"] = "ok" if settings.GOOGLE_API_KEY else "not_configured"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "ok" if all_ok else "degraded",
        "checks": checks,
        "version": settings.APP_VERSION,
        "uptime_seconds": _get_uptime_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/metrics")
async def metrics(db: Session = Depends(get_db)):
    """Basic application metrics for monitoring dashboards."""
    from app.models.db import (
        GenerationRequest,
        User,
    )

    def _count(model, **filters) -> int:
        q = db.query(model)
        for k, v in filters.items():
            q = q.filter(getattr(model, k) == v)
        return q.count()

    # Generation counts
    total_generations = _count(GenerationRequest)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    generations_today = (
        db.query(GenerationRequest)
        .filter(GenerationRequest.created_at >= today_start)
        .count()
    )
    succeeded = _count(GenerationRequest, status="succeeded")
    failed = _count(GenerationRequest, status="failed")

    # User counts
    total_users = _count(User)

    # Queue depth
    queue_depth = 0
    try:
        import redis as _redis
        from rq import Queue
        r = _redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        q = Queue("drapestudio", connection=r)
        queue_depth = len(q)
    except Exception:
        pass

    return {
        "total_users": total_users,
        "total_generations": total_generations,
        "generations_today": generations_today,
        "succeeded": succeeded,
        "failed": failed,
        "queue_depth": queue_depth,
        "uptime_seconds": _get_uptime_seconds(),
    }
