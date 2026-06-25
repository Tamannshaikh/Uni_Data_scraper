"""
Discovery Orchestrator V2 — Uses new extraction architecture.

Integrates the frozen extractor system with the discovery API.
For configured universities, uses manual config.
For unconfigured universities, attempts domain resolution + URL guessing.
"""
import asyncio
import logging
import time
from datetime import datetime, timezone

import database
from pipeline.fetcher import fetch_page
from pipeline.extractors import extract_programs
from UNIVERSITY_CONFIG import UNIVERSITY_CONFIG, is_configured

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


async def run_discovery(discovery_id: str, university_name: str):
    """
    Main discovery orchestrator.
    
    Flow:
    1. Check if university is manually configured
    2. If configured: use config directly
    3. If not: attempt domain resolution + URL guessing
    4. Fetch page and extract programs
    5. Save results to MongoDB
    """
    start_time = time.time()
    col = database.discovery_results_collection
    
    logger.info(f"[discovery_v2] {discovery_id} starting for '{university_name}'")
    
    # Update status to running
    await col.update_one(
        {"discovery_id": discovery_id},
        {"$set": {"status": "running"}}
    )
    
    try:
        # =====================================================================
        # Step 1: Check if manually configured
        # =====================================================================
        
        # Try to find domain in university name
        domain = extract_domain_from_name(university_name)
        
        if domain and is_configured(domain):
            logger.info(f"[discovery_v2] {discovery_id} — found manual config for {domain}")
            config = UNIVERSITY_CONFIG[domain]
            
            # Use manual configuration
            catalog_url = config['url']
            strategy = config['strategy']
            method = "manual_config"
            confidence = "high"
        
        else:
            # =====================================================================
            # Step 2: Attempt domain resolution (fallback to old system)
            # =====================================================================
            logger.info(f"[discovery_v2] {discovery_id} — no manual config, attempting resolution")
            
            from pipeline.domain_resolver import resolve_domain
            domain_result = await resolve_domain(university_name)
            
            if not domain_result or not domain_result.get("domain"):
                # Failed to resolve domain
                elapsed = time.time() - start_time
                await col.update_one(
                    {"discovery_id": discovery_id},
                    {
                        "$set": {
                            "status": "failed",
                            "reason": "Could not resolve university domain",
                            "error": domain_result.get("error") if domain_result else "Unknown error",
                            "elapsed_seconds": round(elapsed, 1),
                        }
                    },
                )
                logger.warning(f"[discovery_v2] {discovery_id} — domain resolution failed")
                return
            
            domain = domain_result["domain"]
            method = domain_result.get("method", "unknown")
            confidence = domain_result.get("confidence", "low")
            
            # Try to find catalog URL (simple heuristic)
            catalog_url = await guess_catalog_url(domain)
            
            if not catalog_url:
                elapsed = time.time() - start_time
                await col.update_one(
                    {"discovery_id": discovery_id},
                    {
                        "$set": {
                            "status": "no_programs_found",
                            "reason": "Could not find graduate catalog URL",
                            "domain": domain,
                            "domain_method": method,
                            "domain_confidence": confidence,
                            "elapsed_seconds": round(elapsed, 1),
                        }
                    },
                )
                logger.warning(f"[discovery_v2] {discovery_id} — catalog URL not found")
                return
            
            # Default strategy for unconfigured universities
            strategy = "anchor"  # Most common
        
        # =====================================================================
        # Step 3: Fetch and extract
        # =====================================================================
        
        logger.info(f"[discovery_v2] {discovery_id} — fetching {catalog_url} with strategy {strategy}")
        
        fetch_result = await fetch_page(catalog_url)
        
        if not fetch_result.get("html"):
            elapsed = time.time() - start_time
            await col.update_one(
                {"discovery_id": discovery_id},
                {
                    "$set": {
                        "status": "failed",
                        "reason": "Failed to fetch catalog page",
                        "error": fetch_result.get("error", "Unknown fetch error"),
                        "domain": domain,
                        "domain_method": method,
                        "domain_confidence": confidence,
                        "elapsed_seconds": round(elapsed, 1),
                    }
                },
            )
            logger.error(f"[discovery_v2] {discovery_id} — fetch failed")
            return
        
        # Extract programs using configured strategy
        programs = extract_programs(
            strategy=strategy,
            base_url=catalog_url,
            html=fetch_result["html"]
        )
        
        # =====================================================================
        # Step 4: Format results
        # =====================================================================
        
        if not programs:
            elapsed = time.time() - start_time
            await col.update_one(
                {"discovery_id": discovery_id},
                {
                    "$set": {
                        "status": "no_programs_found",
                        "reason": "Extractor returned 0 programs",
                        "domain": domain,
                        "domain_method": method,
                        "domain_confidence": confidence,
                        "elapsed_seconds": round(elapsed, 1),
                    }
                },
            )
            logger.warning(f"[discovery_v2] {discovery_id} — 0 programs extracted")
            return
        
        # Format programs for API response
        formatted_programs = []
        for prog in programs[:200]:  # Cap at 200
            formatted_programs.append({
                "program_name": prog["degree_name"],
                "degree_level": infer_degree_level(prog["degree_name"]),
                "url": prog["url"],
            })
        
        # =====================================================================
        # Step 5: Save success
        # =====================================================================
        
        elapsed = time.time() - start_time
        await col.update_one(
            {"discovery_id": discovery_id},
            {
                "$set": {
                    "status": "success",
                    "domain": domain,
                    "domain_method": method,
                    "domain_confidence": confidence,
                    "programs": formatted_programs,
                    "programs_count": len(formatted_programs),
                    "elapsed_seconds": round(elapsed, 1),
                }
            },
        )
        
        logger.info(
            f"[discovery_v2] {discovery_id} — SUCCESS: {len(formatted_programs)} programs "
            f"from {domain} in {elapsed:.1f}s"
        )
    
    except Exception as e:
        elapsed = time.time() - start_time
        logger.exception(f"[discovery_v2] {discovery_id} — exception: {e}")
        await col.update_one(
            {"discovery_id": discovery_id},
            {
                "$set": {
                    "status": "failed",
                    "reason": "Internal error during discovery",
                    "error": str(e),
                    "elapsed_seconds": round(elapsed, 1),
                }
            },
        )


def extract_domain_from_name(university_name: str) -> str | None:
    """
    Extract domain from university name.
    
    Examples:
    - "University of Arkansas" → "uark.edu"
    - "MIT" → "mit.edu"
    - "Purdue University" → "purdue.edu"
    """
    name_lower = university_name.lower()
    
    # Simple mapping for known universities
    domain_map = {
        "arkansas": "uark.edu",
        "mit": "mit.edu",
        "purdue": "purdue.edu",
        "ucsd": "ucsd.edu",
        "stanford": "stanford.edu",
        "manchester": "manchester.ac.uk",
    }
    
    for key, domain in domain_map.items():
        if key in name_lower:
            return domain
    
    return None


async def guess_catalog_url(domain: str) -> str | None:
    """
    Try common catalog URL patterns.
    
    Returns first URL that returns 200 OK.
    """
    patterns = [
        f"https://{domain}/graduate/programs",
        f"https://{domain}/programs",
        f"https://catalog.{domain}/graduate",
        f"https://grad.{domain}/programs",
        f"https://www.{domain}/graduate/programs",
    ]
    
    for url in patterns:
        try:
            result = await fetch_page(url)
            if result.get("html"):
                logger.info(f"[guess_catalog_url] Found working URL: {url}")
                return url
        except Exception:
            continue
    
    return None


def infer_degree_level(program_name: str) -> str:
    """Infer degree level from program name."""
    name_lower = program_name.lower()
    
    if any(x in name_lower for x in ["phd", "ph.d", "doctor"]):
        return "PhD"
    elif any(x in name_lower for x in ["mba", "m.b.a"]):
        return "MBA"
    elif any(x in name_lower for x in ["master", "m.s.", "m.a.", "m.sc.", "m.eng."]):
        return "Master's"
    elif "certificate" in name_lower:
        return "Certificate"
    else:
        return "Graduate"
