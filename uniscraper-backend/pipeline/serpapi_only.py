"""
SERPAPI-ONLY DEGREE EXTRACTOR

The simplest possible approach:
1. Check cache
2. If not cached: Use SerpAPI to find pages
3. Fetch top URLs
4. Extract degrees with simple regex
5. Return results

No SearXNG. No PageType. No confidence. No LLM. No complexity.
"""
import asyncio
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
import httpx
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Cache file for known catalog URLs
CACHE_FILE = Path(__file__).parent.parent / "catalog_cache.json"

# SerpAPI config (using SearXNG as "SerpAPI" since that's what we have)
from pipeline.searxng_client import search_degrees_searxng


def _load_cache() -> Dict[str, List[str]]:
    """Load URL cache."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                data.pop('comment', None)
                return data
        return {}
    except Exception as e:
        logger.warning(f"Cache load failed: {e}")
        return {}


def _save_cache(cache: Dict[str, List[str]]):
    """Save URL cache."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'comment': 'Known catalog URLs. Auto-populated on success.',
                **cache
            }, f, indent=2)
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


def _add_to_cache(domain: str, url: str):
    """Add URL to cache."""
    cache = _load_cache()
    if domain not in cache:
        cache[domain] = []
    if url not in cache[domain]:
        cache[domain].append(url)
        _save_cache(cache)
        logger.info(f"[cache] Added {url}")


def _rank_url(url: str) -> int:
    """
    Rank URL by how likely it contains degree listings.
    
    Higher score = better.
    """
    url_lower = url.lower()
    
    score = 0
    
    # GOOD indicators
    good_keywords = [
        'catalog', 'programs', 'degrees', 'graduate', 
        'academics', 'courses', 'study', 'masters',
        'doctoral', 'phd', 'postgraduate'
    ]
    for keyword in good_keywords:
        if keyword in url_lower:
            score += 3
    
    # BAD indicators (waste of time)
    bad_keywords = [
        'news', 'events', 'funding', 'admissions', 'tuition',
        'calendar', 'about', 'faculty', 'directory', 'staff',
        'research', 'apply', 'application', 'requirements',
        'financial', 'aid', 'scholarships', 'blog', 'article'
    ]
    for keyword in bad_keywords:
        if keyword in url_lower:
            score -= 5
    
    return score


async def extract_degrees_serpapi(domain: str, max_results: int = 100) -> Dict:
    """
    Extract degrees using SerpAPI only.
    
    Returns:
        {
            'domain': str,
            'degrees': List[Dict],
            'cache_hit': bool,
            'urls_tried': List[str],
            'total_time_ms': int
        }
    """
    import time
    start_time = time.time()
    
    result = {
        'domain': domain,
        'degrees': [],
        'cache_hit': False,
        'urls_tried': [],
        'serpapi_queries': 0,
        'total_time_ms': 0
    }
    
    logger.info(f"[serpapi_only] Starting for {domain}")
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 0: Check cache
    # ═══════════════════════════════════════════════════════════════════
    cache = _load_cache()
    cached_urls = cache.get(domain, [])
    
    if cached_urls:
        logger.info(f"[serpapi_only] CACHE HIT: {len(cached_urls)} URLs")
        result['cache_hit'] = True
        
        # Try cached URLs
        degrees = await _extract_from_urls(cached_urls[:3], domain)
        
        if len(degrees) >= 10:
            result['degrees'] = degrees[:max_results]
            result['urls_tried'] = cached_urls[:3]
            result['total_time_ms'] = int((time.time() - start_time) * 1000)
            logger.info(f"[serpapi_only] Cache success: {len(degrees)} degrees")
            return result
        
        logger.info(f"[serpapi_only] Cache returned only {len(degrees)} degrees, trying search")
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 1: SerpAPI search
    # ═══════════════════════════════════════════════════════════════════
    logger.info(f"[serpapi_only] Searching with SerpAPI...")
    
    # 6-8 focused queries
    queries = [
        f'site:{domain} graduate programs',
        f'site:{domain} masters programs',
        f'site:{domain} doctoral programs',
        f'site:{domain} graduate catalog',
        f'site:{domain} programs of study',
        f'site:{domain} degree programs',
        f'site:{domain} graduate degrees',
    ]
    
    result['serpapi_queries'] = len(queries)
    
    # Search
    search_results = []
    for query in queries:
        try:
            results = await search_degrees_searxng(domain, [query])
            search_results.extend(results)
        except Exception as e:
            logger.warning(f"[serpapi_only] Search failed for '{query}': {e}")
    
    if not search_results:
        logger.error(f"[serpapi_only] No search results")
        result['total_time_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    logger.info(f"[serpapi_only] Got {len(search_results)} search results")
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 2: Rank and filter URLs
    # ═══════════════════════════════════════════════════════════════════
    urls_with_scores = []
    seen_urls = set()
    
    for res in search_results:
        url = res.get('url', '')
        if not url or url in seen_urls:
            continue
        
        # Only domain URLs
        if domain not in url.lower():
            continue
        
        seen_urls.add(url)
        score = _rank_url(url)
        
        if score > 0:  # Only keep positive scores
            urls_with_scores.append((score, url))
    
    # Sort by score, take top 5
    urls_with_scores.sort(reverse=True, key=lambda x: x[0])
    top_urls = [url for score, url in urls_with_scores[:5]]
    
    if not top_urls:
        logger.warning(f"[serpapi_only] No good URLs found after ranking")
        result['total_time_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    logger.info(f"[serpapi_only] Top {len(top_urls)} URLs:")
    for i, url in enumerate(top_urls, 1):
        logger.info(f"  {i}. {url[:80]}")
    
    result['urls_tried'] = top_urls
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 3: Fetch and extract
    # ═══════════════════════════════════════════════════════════════════
    degrees = await _extract_from_urls(top_urls, domain)
    
    # ═══════════════════════════════════════════════════════════════════
    # TIER 4: Cache successful URL
    # ═══════════════════════════════════════════════════════════════════
    if len(degrees) >= 20 and top_urls:
        _add_to_cache(domain, top_urls[0])
    
    result['degrees'] = degrees[:max_results]
    result['total_time_ms'] = int((time.time() - start_time) * 1000)
    
    logger.info(f"[serpapi_only] Final: {len(result['degrees'])} degrees")
    
    return result


async def _extract_from_urls(urls: List[str], domain: str) -> List[Dict]:
    """
    Fetch URLs and extract program links.
    
    Returns: List of {degree_name, url}
    """
    from pipeline.link_extractor import extract_program_links, deduplicate_programs
    
    all_programs = []
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for url in urls:
            try:
                logger.info(f"[serpapi_only] Fetching {url[:60]}...")
                resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                
                if resp.status_code != 200:
                    continue
                
                # Extract program links
                programs = extract_program_links(str(resp.url), resp.text)
                
                logger.info(f"[serpapi_only] Extracted {len(programs)} program links from {url[:60]}")
                all_programs.extend(programs)
                
                # If we got enough, stop
                if len(all_programs) >= 100:
                    break
            
            except Exception as e:
                logger.warning(f"[serpapi_only] Failed to fetch {url[:60]}: {e}")
                continue
    
    # Deduplicate
    unique_programs = deduplicate_programs(all_programs)
    
    logger.info(f"[serpapi_only] Total unique: {len(unique_programs)}")
    
    return unique_programs


# ═══════════════════════════════════════════════════════════════════════════
# Convenience API
# ═══════════════════════════════════════════════════════════════════════════

async def extract_degrees(domain: str) -> List[Dict]:
    """
    Simple API: Just give me the degrees.
    
    Returns: List of {degree_name, url}
    """
    result = await extract_degrees_serpapi(domain)
    return result['degrees']


# ═══════════════════════════════════════════════════════════════════════════
# Test
# ═══════════════════════════════════════════════════════════════════════════

async def test():
    """Test on a few universities."""
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    test_domains = [
        "mit.edu",
        "uark.edu",
        "manchester.ac.uk",
    ]
    
    for domain in test_domains:
        print(f"\n{'='*80}")
        print(f"TESTING: {domain.upper()}")
        print('='*80 + "\n")
        
        result = await extract_degrees_serpapi(domain, max_results=20)
        
        print(f"Cache hit: {result['cache_hit']}")
        print(f"Queries: {result['serpapi_queries']}")
        print(f"Time: {result['total_time_ms']/1000:.1f}s")
        print(f"Degrees: {len(result['degrees'])}")
        
        if result['degrees']:
            print(f"\nSample (first 10):")
            for i, deg in enumerate(result['degrees'][:10], 1):
                print(f"  {i}. {deg['degree_name'][:70]}")
        else:
            print("\n[WARNING] No degrees found!")
        
        print()


if __name__ == "__main__":
    asyncio.run(test())
