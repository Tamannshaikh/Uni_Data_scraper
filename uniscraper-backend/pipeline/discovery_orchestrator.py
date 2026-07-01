# pipeline/discovery_orchestrator.py
# Orchestrates the full Phase 2 discovery pipeline:
#   1. Resolve university name → domain
#   2. Discover program pages on that domain
#   3. Save results to MongoDB (with 24h cache)

import logging
import time
from datetime import datetime, timezone

import database
from pipeline.domain_resolver import resolve_university_domain
from pipeline.simple_discovery import discover_programs_simple

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_discovery(discovery_id: str, university_name: str) -> None:
    """
    Full discovery pipeline. Runs as a FastAPI BackgroundTask.
    Never raises — all exceptions are caught and written to MongoDB.
    """
    start_time = time.monotonic()
    col = database.discovery_results_collection

    try:
        # ── Mark as running ───────────────────────────────────────────────────
        await col.update_one(
            {"discovery_id": discovery_id},
            {"$set": {"status": "running", "started_at": _utcnow()}},
        )

        # ── Step 1: Resolve domain ────────────────────────────────────────────
        logger.info(f"[discovery_orchestrator] {discovery_id} — resolving domain for '{university_name}'")
        domain_result = await resolve_university_domain(university_name)

        if not domain_result.get("domain") or domain_result["confidence"] == "low":
            elapsed = round(time.monotonic() - start_time, 2)
            await col.update_one(
                {"discovery_id": discovery_id},
                {
                    "$set": {
                        "status": "failed",
                        "reason": "domain_not_found",
                        "error": f"Could not resolve domain for '{university_name}'",
                        "completed_at": _utcnow(),
                        "elapsed_seconds": elapsed,
                    }
                },
            )
            logger.warning(
                f"[discovery_orchestrator] {discovery_id} — domain resolution failed"
            )
            return

        domain = domain_result["domain"]
        domain_method = domain_result["method"]
        domain_confidence = domain_result["confidence"]

        logger.info(
            f"[discovery_orchestrator] {discovery_id} — resolved domain: "
            f"{domain} (method={domain_method}, confidence={domain_confidence})"
        )

        await col.update_one(
            {"discovery_id": discovery_id},
            {"$set": {
                "domain": domain,
                "domain_method": domain_method,
                "domain_confidence": domain_confidence,
            }},
        )

        # ── Step 2: Discover programs ─────────────────────────────────────────
        logger.info(
            f"[discovery_orchestrator] {discovery_id} — discovering programs on {domain}"
        )
        programs = await discover_programs_simple(
            domain=domain,
            university_name=university_name,
            max_catalog_pages=12,
        )

        elapsed = round(time.monotonic() - start_time, 2)

        if not programs:
            await col.update_one(
                {"discovery_id": discovery_id},
                {
                    "$set": {
                        "status": "no_programs_found",
                        "programs": [],
                        "programs_count": 0,
                        "completed_at": _utcnow(),
                        "elapsed_seconds": elapsed,
                    }
                },
            )
            logger.warning(
                f"[discovery_orchestrator] {discovery_id} — no programs found on {domain}"
            )
            return

        # ── Step 3: Save results ──────────────────────────────────────────────
        await col.update_one(
            {"discovery_id": discovery_id},
            {
                "$set": {
                    "status": "success",
                    "programs": programs,
                    "programs_count": len(programs),
                    "completed_at": _utcnow(),
                    "elapsed_seconds": elapsed,
                }
            },
        )

        logger.info(
            f"[discovery_orchestrator] {discovery_id} — success, "
            f"{len(programs)} programs found in {elapsed}s"
        )

    except Exception as exc:
        elapsed = round(time.monotonic() - start_time, 2)
        logger.exception(
            f"[discovery_orchestrator] {discovery_id} — unhandled exception: {exc}"
        )
        try:
            await col.update_one(
                {"discovery_id": discovery_id},
                {
                    "$set": {
                        "status": "failed",
                        "reason": "internal_error",
                        "error": str(exc),
                        "completed_at": _utcnow(),
                        "elapsed_seconds": elapsed,
                    }
                },
            )
        except Exception as db_exc:
            logger.error(
                f"[discovery_orchestrator] {discovery_id} — MongoDB update failed: {db_exc}"
            )
