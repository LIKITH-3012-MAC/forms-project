"""
Health Check Endpoints
======================
Provides health and readiness probes for the Sakra Forms backend.

Endpoints:
- GET /api/health          — Basic liveness check
- GET /api/health/detailed — Detailed system status (protected)
- GET /api/health/db       — Database connectivity check
- GET /api/health/services — External service configuration check
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from database import engine, SessionLocal
from config import settings

router = APIRouter(prefix="/api/health", tags=["health"])

APP_VERSION = "2.0.0"


@router.get("")
async def health_check():
    """
    Basic liveness probe.
    Returns a simple status with timestamp and version.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION,
    }


@router.get("/detailed")
async def health_detailed(key: str = Query(default=None)):
    """
    Detailed health check with database stats and table counts.
    Protected by a query parameter `key` that must match the SECRET_KEY
    environment variable.
    """
    secret_key = os.getenv("SECRET_KEY", "")

    if not key or key != secret_key:
        raise HTTPException(status_code=403, detail="Invalid or missing secret key")

    result = {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": APP_VERSION,
        "database": {},
        "pool": {},
        "tables": {},
    }

    # Database connectivity and stats
    db = SessionLocal()
    try:
        # Ping
        db.execute(text("SELECT 1"))
        result["database"]["connected"] = True

        # Connection pool stats
        pool = engine.pool
        result["pool"] = {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }

        # Table row counts
        tables_result = db.execute(
            text("SHOW TABLES")
        ).fetchall()

        for (table_name,) in tables_result:
            count_result = db.execute(
                text(f"SELECT COUNT(*) FROM `{table_name}`")
            ).scalar()
            result["tables"][table_name] = count_result

    except Exception as e:
        result["status"] = "degraded"
        result["database"]["connected"] = False
        result["database"]["error"] = str(e)
    finally:
        db.close()

    return result


@router.get("/db")
async def health_db():
    """
    Database connectivity check (ping only).
    """
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        db.close()


@router.get("/services")
async def health_services():
    """
    Check whether external service API keys are configured.
    """
    resend_configured = bool(os.getenv("RESEND_API_KEY"))
    omni_configured = bool(os.getenv("OMNI_API_KEY"))

    all_configured = resend_configured and omni_configured

    return {
        "status": "ok" if all_configured else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "resend_email": {
                "configured": resend_configured,
            },
            "omni_ai": {
                "configured": omni_configured,
            },
        },
    }
