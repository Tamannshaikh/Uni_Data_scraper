# routers/discover.py
# POST /api/v1/discover  — start a university program discovery
# GET  /api/v1/discover/{discovery_id} — poll for results

import re
import uuid
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, BackgroundTasks, HTTPException

import database
from models.discover_request import DiscoverRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["discover"])

_CACHE_TTL_HOURS = 24


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_name(name: str) -> str:
    """Lowercase + collapse whitespace for cache key."""
    return re.sub(r"\s+", " ", name.strip().lower())


@router.post("/discover", status_code=202)
async def start_discovery(request: DiscoverRequest, background_tasks: BackgroundTasks):
    """
    Start a university program discovery.
    Returns immediately with discovery_id. Poll GET /discover/{id} for results.
    Cached for 24h per university name.
    """
    norm_name = _normalize_name(request.university_name)
    col = database.discovery_results_collection

    # ── Cache check ───────────────────────────────────────────────────────────
    cutoff = _utcnow() - timedelta(hours=_CACHE_TTL_HOURS)
    existing = await col.find_one(
        {
            "university_name_normalized": norm_name,
            "status": {"$in": ["success", "no_programs_found"]},
            "created_at": {"$gte": cutoff},
        },
        sort=[("created_at", -1)],
    )
    if existing:
        cached_id = existing["discovery_id"]
        logger.info(f"[discover] cache hit for '{norm_name}' -> {cached_id}")
        return {
            "discovery_id": cached_id,
            "status": "cached",
            "cached_from": cached_id,
        }

    # ── New discovery ─────────────────────────────────────────────────────────
    discovery_id = str(uuid.uuid4())

    initial_doc = {
        "discovery_id": discovery_id,
        "university_name": request.university_name,
        "university_name_normalized": norm_name,
        "status": "processing",
        "created_at": _utcnow(),
        "domain": None,
        "domain_method": None,
        "domain_confidence": None,
        "programs": [],
        "programs_count": 0,
        "error": None,
        "reason": None,
        "elapsed_seconds": None,
    }
    await col.insert_one(initial_doc)
    logger.info(f"[discover] queued {discovery_id} for '{request.university_name}'")

    from pipeline.discovery_orchestrator import run_discovery
    background_tasks.add_task(run_discovery, discovery_id, request.university_name)

    return {"discovery_id": discovery_id, "status": "processing"}


@router.get("/discover/{discovery_id}")
async def get_discovery(discovery_id: str):
    """
    Poll for discovery results.
    Status: processing → running → success | failed | no_programs_found
    """
    col = database.discovery_results_collection
    doc = await col.find_one({"discovery_id": discovery_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="Discovery not found")

    doc.pop("_id", None)
    doc.pop("university_name_normalized", None)
    return doc
