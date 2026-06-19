# pipeline/serpapi_client.py
# SerpAPI client for Phase 2 program discovery.
# Used as a FALLBACK ONLY when direct path-guessing fails (e.g. Cloudflare blocks).
# Tracks monthly usage to stay within free tier (~100 searches/month).

import logging
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)

SKIP_DOMAINS = [
    "wikipedia.org", "linkedin.com", "facebook.com",
    "youtube.com", "twitter.com", "x.com", "instagram.com",
    "reddit.com", "quora.com", "niche.com", "collegeboard.org",
    "usnews.com", "topuniversities.com", "timeshighereducation.com",
]


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


async def _track_usage() -> None:
    """Increment monthly SerpAPI call counter in MongoDB."""
    try:
        import database
        month = _current_month()
        result = await database.api_usage_collection.find_one_and_update(
            {"service": "serpapi", "month": month},
            {"$inc": {"call_count": 1}},
            upsert=True,
            return_document=True,
        )
        count = result.get("call_count", 1) if result else 1
        if count >= 80:
            logger.warning(
                f"[serpapi_client] Approaching free tier limit: {count} calls this month ({month})"
            )
    except Exception as e:
        logger.debug(f"[serpapi_client] Usage tracking failed (non-critical): {e}")


async def search_program_pages(domain: str, university_name: str) -> list[str]:
    """
    Use SerpAPI to find program listing pages on a domain that's blocking
    direct HEAD/GET requests (e.g. behind Cloudflare).
    Returns a list of candidate URLs to verify and use as BFS seeds.
    Runs up to 2 queries to maximize results while staying within free tier.
    """
    if not settings.serpapi_key or not settings.serpapi_enabled:
        logger.warning("[serpapi_client] No SERPAPI_KEY configured or disabled")
        return []

    # Two targeted queries: one for graduate/masters individual pages, one for general index
    queries = [
        f'site:{domain} (masters OR phd OR "master of" OR msc OR mba) program',
        f'site:{domain} (programs OR courses OR degrees OR study OR graduate)',
    ]

    all_urls: list[str] = []

    for query in queries:
        try:
            await _track_usage()
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": settings.serpapi_key,
                        "num": 10,
                        "engine": "google",
                    },
                )
                response.raise_for_status()
                data = response.json()

            organic = data.get("organic_results", [])
            urls = [r.get("link") for r in organic if r.get("link")]
            logger.info(
                f"[serpapi_client] query='{query[:70]}' returned {len(urls)} URLs"
            )
            all_urls.extend(urls)

        except Exception as e:
            logger.error(f"[serpapi_client] search_program_pages query failed: {e}")
            continue

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped = []
    for u in all_urls:
        if u not in seen:
            seen.add(u)
            deduped.append(u)

    logger.info(
        f"[serpapi_client] program_pages total: {len(deduped)} unique URLs for {domain}"
    )
    return deduped


async def search_university_domain(university_name: str) -> str | None:
    """
    Fallback domain resolution via SerpAPI when heuristic guessing fails.
    Returns the domain string (e.g. 'unimelb.edu.au') or None.
    """
    if not settings.serpapi_key or not settings.serpapi_enabled:
        return None

    query = f"{university_name} official university website"

    try:
        await _track_usage()
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": settings.serpapi_key,
                    "num": 5,
                    "engine": "google",
                },
            )
            response.raise_for_status()
            data = response.json()

        from urllib.parse import urlparse

        organic = data.get("organic_results", [])
        for result in organic:
            link = result.get("link", "")
            if not link:
                continue
            if any(skip in link for skip in SKIP_DOMAINS):
                continue
            domain = urlparse(link).netloc.replace("www.", "")
            if domain:
                logger.info(
                    f"[serpapi_client] domain resolved: {university_name} → {domain}"
                )
                return domain

        return None

    except Exception as e:
        logger.error(f"[serpapi_client] search_university_domain failed: {e}")
        return None
