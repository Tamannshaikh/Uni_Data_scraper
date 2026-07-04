"""
Smart Degree Extractor - Layered strategy with minimal API usage.

TIER 0: Cached URLs (instant, 0 cost) - with JS rendering support for top universities
TIER 1: URL Pattern Guessing (fast, 0 cost)
TIER 2: Static extraction from discovered pages
TIER 3: Link Following (medium, 0 cost) - with URL filtering
TIER 4: SerpAPI Discovery (3-5 queries, low cost)

Strategy automatically escalates only when needed.
80% of universities should never hit paid APIs.
"""
import asyncio
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

# Import top 50 universities config
from top_universities_urls import get_top_university_config

logger = logging.getLogger(__name__)

# Cache file for known catalog URLs
CACHE_FILE = Path(__file__).parent.parent / "catalog_cache.json"


def _load_catalog_cache() -> Dict[str, List[str]]:
    """Load catalog URL cache from disk."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Remove comment field
                data.pop('comment', None)
                return data
        return {}
    except Exception as e:
        logger.warning(f"Failed to load catalog cache: {e}")
        return {}


def _save_catalog_cache(cache: Dict[str, List[str]]):
    """Save catalog URL cache to disk."""
    try:
        with open(CACHE_FILE, 'w') as f:
            data = {
                'comment': 'Known catalog/program URLs for universities. Populated automatically on successful extraction.',
                **cache
            }
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save catalog cache: {e}")


def _add_to_cache(domain: str, url: str):
    """Add a successful catalog URL to the cache."""
    cache = _load_catalog_cache()
    
    if domain not in cache:
        cache[domain] = []
    
    if url not in cache[domain]:
        cache[domain].append(url)
        _save_catalog_cache(cache)
        logger.info(f"[cache] Added {url} to catalog cache for {domain}")


async def extract_degrees_smart(domain: str, max_results: int = 100) -> Dict:
    """
    Smart extraction that tries multiple strategies automatically.
    
    Args:
        domain: University domain (e.g., "mit.edu", "purdue.edu")
        max_results: Maximum number of degrees to return
    
    Returns:
        {
            'domain': str,
            'degrees': List[Dict],
            'strategy_used': str,  # 'catalog_static', 'catalog_playwright', 'search'
            'catalog_urls_tried': List[str],
            'total_time_ms': int
        }
    """
    import time
    start_time = time.time()
    
    from pipeline.catalog_url_guesser import find_catalog_pages
    from pipeline.simple_extractor import extract_degrees_simple, deduplicate_degrees
    
    result = {
        'domain': domain,
        'degrees': [],
        'strategy_used': None,
        'catalog_urls_tried': [],
        'catalog_url_success': None,
        'static_success': False,
        'playwright_used': False,
        'serpapi_used': False,
        'cache_hit': False,
        'confidence': 0.0,
        'total_time_ms': 0,
        'tier_timings': {}
    }
    
    logger.info(f"[smart_extract] Starting extraction for {domain}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # CHECK: Special handler for this university?
    # ──────────────────────────────────────────────────────────────────────────
    from pipeline.university_adapters import SPECIAL_HANDLERS
    
    if domain in SPECIAL_HANDLERS:
        logger.info(f"[smart_extract] Using special handler for {domain}")
        
        try:
            degrees = await SPECIAL_HANDLERS[domain]()
            
            if len(degrees) >= 10:
                result['strategy_used'] = 'special_handler'
                result['degrees'] = degrees[:max_results]
                result['confidence'] = 0.90  # Special handlers are high confidence
                result['total_time_ms'] = int((time.time() - start_time) * 1000)
                
                logger.info(f"[smart_extract] Special handler succeeded: {len(degrees)} degrees")
                return result
            else:
                logger.warning(f"[smart_extract] Special handler returned only {len(degrees)} degrees, falling back to generic pipeline")
        
        except Exception as e:
            logger.error(f"[smart_extract] Special handler failed: {e}, falling back to generic pipeline")
    
    # ──────────────────────────────────────────────────────────────────────────
    # TIER 0: Check cache first (instant, 0 cost) + Check if JS rendering needed
    # ──────────────────────────────────────────────────────────────────────────
    cache = _load_catalog_cache()
    cached_urls = cache.get(domain, [])
    
    # Check if this is a top university that needs JS rendering
    top_uni_config = get_top_university_config(domain)
    needs_js_rendering = top_uni_config and top_uni_config.get('render_js', False)
    
    if cached_urls:
        logger.info(f"[smart_extract] TIER 0: Found {len(cached_urls)} cached URL(s)")
        result['cache_hit'] = True
        
        if needs_js_rendering:
            logger.info(f"[smart_extract] TIER 0: JS rendering enabled for {domain}")
        
        # Try cached URLs directly
        catalog_pages = []
        import httpx
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for url in cached_urls[:3]:  # Try first 3 cached URLs
                try:
                    resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                    if resp.status_code == 200:
                        catalog_pages.append({
                            'url': str(resp.url),
                            'content': resp.text,
                            'status': resp.status_code,
                            'has_degrees': True,
                            'score': 100  # Cache hit = highest score
                        })
                        logger.info(f"[smart_extract] TIER 0: Cache hit for {url[:60]}")
                except Exception as e:
                    logger.debug(f"[smart_extract] TIER 0: Cached URL failed: {e}")
        
        if catalog_pages:
            # Try extraction from cached pages
            all_degrees = []
            
            for page in catalog_pages:
                # Use SIMPLE extractor - no scoring, no filtering
                degrees = extract_degrees_simple(page['url'], page['content'])
                all_degrees.extend(degrees)
                
                if len(all_degrees) >= 10:
                    logger.info(f"[smart_extract] TIER 0: SUCCESS - cache hit with {len(all_degrees)} degrees")
                    result['strategy_used'] = 'cache_hit'
                    result['catalog_url_success'] = page['url']
                    result['catalog_urls_tried'] = [p['url'] for p in catalog_pages]
                    result['degrees'] = deduplicate_degrees(all_degrees)[:max_results]
                    result['confidence'] = _calculate_confidence(result['degrees'], 'static')
                    result['total_time_ms'] = int((time.time() - start_time) * 1000)
                    return result
            
            logger.info(f"[smart_extract] TIER 0: Cache found {len(all_degrees)} degrees (threshold: 10)")
    else:
        logger.info(f"[smart_extract] TIER 0: No cached URLs for {domain}")
    
    # ──────────────────────────────────────────────────────────────────────────
    # TIER 1: URL pattern guessing (fast, 0 cost)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info(f"[smart_extract] TIER 1: URL pattern guessing...")
    
    from pipeline.catalog_url_guesser import find_catalog_pages
    catalog_pages = await find_catalog_pages(domain, max_concurrent=10)
    logger.info(f"[smart_extract] TIER 1: Found {len(catalog_pages)} pages via URL guessing")
    
    if not catalog_pages:
        logger.info(f"[smart_extract] TIER 1: No catalog pages found via URL guessing")
    
    # ──────────────────────────────────────────────────────────────────────────
    # TIER 2: Static extraction on discovered pages
    # ──────────────────────────────────────────────────────────────────────────
    if catalog_pages:
        logger.info(f"[smart_extract] TIER 2: Static extraction on {len(catalog_pages)} pages...")
        
        from pipeline.simple_extractor import extract_degrees_simple
        
        all_degrees = []
        
        for page in catalog_pages[:3]:  # Try first 3 pages
            degrees = extract_degrees_simple(page['url'], page['content'])
            all_degrees.extend(degrees)
            
            if len(all_degrees) >= 20:  # Good threshold
                logger.info(f"[smart_extract] TIER 2: SUCCESS - found {len(all_degrees)} degrees")
                result['strategy_used'] = 'catalog_static'
                result['static_success'] = True
                result['catalog_url_success'] = page['url']
                result['catalog_urls_tried'] = [p['url'] for p in catalog_pages[:3]]
                result['degrees'] = deduplicate_degrees(all_degrees)[:max_results]
                result['confidence'] = _calculate_confidence(result['degrees'], 'static')
                result['total_time_ms'] = int((time.time() - start_time) * 1000)
                
                # Add to cache for future use
                _add_to_cache(domain, page['url'])
                
                return result
        
        logger.info(f"[smart_extract] TIER 2: Found {len(all_degrees)} degrees (threshold: 20)")
        
        # ──────────────────────────────────────────────────────────────────────
        # TIER 3: Link following (landing page detection)
        # ──────────────────────────────────────────────────────────────────────
        if len(all_degrees) < 20:
            logger.info(f"[smart_extract] TIER 3: Following internal links...")
            
            linked_degrees = await _follow_catalog_links(catalog_pages[:2], max_links=20)
            all_degrees.extend(linked_degrees)
            
            if len(all_degrees) >= 20:
                logger.info(f"[smart_extract] TIER 3: SUCCESS - found {len(all_degrees)} degrees via link following")
                result['strategy_used'] = 'catalog_static_deep'
                result['static_success'] = True
                result['catalog_url_success'] = catalog_pages[0]['url']
                result['catalog_urls_tried'] = [p['url'] for p in catalog_pages[:2]]
                result['degrees'] = deduplicate_degrees(all_degrees)[:max_results]
                result['confidence'] = _calculate_confidence(result['degrees'], 'static')
                result['total_time_ms'] = int((time.time() - start_time) * 1000)
                
                # Add to cache
                _add_to_cache(domain, catalog_pages[0]['url'])
                
                return result
            
            logger.info(f"[smart_extract] TIER 3: Still only {len(all_degrees)} degrees after link following")
    
    # ──────────────────────────────────────────────────────────────────────────
    # TIER 4: SerpAPI discovery (3-5 queries only, last resort)
    # ──────────────────────────────────────────────────────────────────────────
    logger.info(f"[smart_extract] TIER 4: SerpAPI discovery (last resort)...")
    
    serpapi_degrees = await _tier4_serpapi_discovery(domain)
    
    # Combine with any degrees found so far
    if 'all_degrees' in locals():
        all_degrees.extend(serpapi_degrees)
    else:
        all_degrees = serpapi_degrees
    
    result['strategy_used'] = 'serpapi_discovery'
    result['serpapi_used'] = True
    result['degrees'] = deduplicate_degrees(all_degrees)[:max_results]
    result['confidence'] = _calculate_confidence(result['degrees'], 'search')
    result['total_time_ms'] = int((time.time() - start_time) * 1000)
    
    logger.info(f"[smart_extract] TIER 4: Final count = {len(result['degrees'])} degrees")
    
    return result


async def _tier4_serpapi_discovery(domain: str) -> List[Dict]:
    """
    Tier 4: Use SerpAPI to discover program pages (3-5 queries only).
    
    This is the last resort for difficult universities.
    Most universities should never reach this tier.
    
    Args:
        domain: University domain
    
    Returns:
        List of degrees extracted from discovered pages
    """
    try:
        from pipeline.simple_degree_search import search_degrees_serpapi
        
        # Extract university name for better queries
        university_name = domain.split('.')[0].title()
        
        # Focused discovery queries (3-5 queries only)
        queries = [
            f'{university_name} graduate programs',
            f'{university_name} graduate catalog',
            f'{university_name} master programs',
            f'{university_name} doctoral programs',
            f'{university_name} degree programs',
        ]
        
        logger.info(f"[tier4] Using SerpAPI for discovery (5 queries)")
        search_results = await search_degrees_serpapi(domain, queries)
        
        if not search_results:
            logger.warning(f"[tier4] SerpAPI returned no results")
            return []
        
        logger.info(f"[tier4] SerpAPI returned {len(search_results)} results")
        
        # Fetch and extract from the actual pages (not just snippets)
        import httpx
        degrees = []
        seen_urls = set()
        
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for result in search_results[:15]:  # Top 15 results
                url = result.get('url', '')
                if not url or url in seen_urls:
                    continue
                
                seen_urls.add(url)
                
                # Skip non-domain URLs
                if domain not in url.lower():
                    continue
                
                try:
                    resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                    if resp.status_code != 200:
                        continue
                    
                    # Try to extract degrees from this page - USE SIMPLE EXTRACTOR
                    page_degrees = extract_degrees_simple(url, resp.text)
                    
                    if page_degrees:
                        logger.info(f"[tier4] Found {len(page_degrees)} degrees at {url[:60]}")
                        degrees.extend(page_degrees)
                        
                        # If we found a good page, add it to cache
                        if len(page_degrees) >= 10:
                            _add_to_cache(domain, url)
                
                except Exception as e:
                    logger.debug(f"[tier4] Failed to fetch {url[:60]}: {e}")
                    continue
        
        logger.info(f"[tier4] Extracted {len(degrees)} degrees from SerpAPI-discovered pages")
        return degrees
        
    except Exception as e:
        logger.error(f"[tier4] SerpAPI discovery failed: {e}")
        return []


async def _follow_catalog_links(catalog_pages: List[Dict], max_links: int = 20) -> List[Dict]:
    """
    Follow internal links from catalog landing pages to find actual degree listings.
    
    Strategy:
    1. Extract all internal links from landing page
    2. Filter out obvious non-program pages (news, events, funding, etc.)
    3. Score remaining links by relevance (prefer /programs/, /degrees/, etc.)
    4. Fetch top N links
    5. Extract degrees from those pages
    
    Args:
        catalog_pages: List of catalog landing pages
        max_links: Maximum links to follow per page
    
    Returns:
        List of degrees found by following links
    """
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    import httpx
    
    # URLs to SKIP (waste of time - these never contain degree listings)
    SKIP_URL_PATTERNS = [
        "/news", "/events", "/event", "/funding", "/incoming", "/resources",
        "/orientation", "/spotlight", "/appreciation", "/conference", "/fellows",
        "/grants", "/handbook", "/policies", "/forms", "/financial", "/aid",
        "/tuition", "/calendar", "/student-life", "/about", "/faculty", "/staff",
        "/contact", "/directory", "/leadership", "/dean", "/mission", "/history",
        "/facilities", "/campus", "/visit", "/apply", "/application", "/admissions",
        "/requirements", "/deadline", "/faq", "/register", "/enroll"
    ]
    
    all_degrees = []
    
    for landing_page in catalog_pages[:2]:  # Top 2 landing pages
        try:
            soup = BeautifulSoup(landing_page['content'], 'html.parser')
            base_url = landing_page['url']
            base_domain = urlparse(base_url).netloc
            
            # Find all internal links
            internal_links = []
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                full_url = urljoin(base_url, href)
                
                # Only internal links
                if urlparse(full_url).netloc != base_domain:
                    continue
                
                # SKIP non-program pages (news, events, funding, etc.)
                lower_url = full_url.lower()
                if any(skip_pattern in lower_url for skip_pattern in SKIP_URL_PATTERNS):
                    continue
                
                # Score link by URL patterns
                score = 0
                lower_url = full_url.lower()
                
                if '/programs/' in lower_url: score += 5
                if '/degrees/' in lower_url: score += 5
                if '/graduate/' in lower_url: score += 3
                if '/masters/' in lower_url or '/phd/' in lower_url: score += 4
                if '/catalog/' in lower_url: score += 3
                if '/academic' in lower_url: score += 2
                
                # Negative scores for non-degree pages
                if '/admissions/' in lower_url: score -= 3
                if '/apply/' in lower_url: score -= 3
                if '/about/' in lower_url: score -= 2
                
                if score > 0:
                    internal_links.append((score, full_url, link.get_text(strip=True)[:100]))
            
            # Sort by score, take top N
            internal_links.sort(reverse=True, key=lambda x: x[0])
            top_links = internal_links[:max_links]
            
            logger.info(f"[tier3] Following {len(top_links)} internal links from {base_url[:60]}...")
            
            # Fetch and extract from each link
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                for score, url, text in top_links:
                    try:
                        resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
                        if resp.status_code == 200:
                            # Extract degrees from this page - USE SIMPLE EXTRACTOR
                            degrees = extract_degrees_simple(url, resp.text)
                            
                            if degrees:
                                logger.debug(f"[tier3] Found {len(degrees)} degrees at {url[:60]}")
                                all_degrees.extend(degrees)
                    
                    except Exception as e:
                        logger.debug(f"[tier3] Failed to fetch {url[:60]}: {e}")
                        continue
        
        except Exception as e:
            logger.warning(f"[tier3] Error following links: {e}")
            continue
    
    logger.info(f"[tier3] Total degrees found by following links: {len(all_degrees)}")
    return all_degrees


def _calculate_confidence(degrees: List[Dict], strategy: str) -> float:
    """
    Calculate confidence score based on number of degrees and extraction strategy.
    
    Args:
        degrees: List of extracted degrees
        strategy: 'static', 'playwright', or 'search'
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    count = len(degrees)
    
    # Base confidence by strategy
    strategy_base = {
        'static': 0.90,      # High confidence - direct HTML extraction
        'playwright': 0.85,  # Good confidence - JS rendering worked
        'search': 0.70       # Lower confidence - indirect extraction
    }
    
    base = strategy_base.get(strategy, 0.60)
    
    # Adjust by count
    if count >= 30:
        return min(base + 0.05, 0.95)  # Very high count
    elif count >= 20:
        return base
    elif count >= 10:
        return base - 0.05
    elif count >= 5:
        return base - 0.15
    else:
        return max(base - 0.30, 0.40)  # Low count = low confidence
    
    return base


# ──────────────────────────────────────────────────────────────────────────────
# Convenience functions
# ──────────────────────────────────────────────────────────────────────────────

async def extract_degrees(domain: str) -> List[Dict]:
    """
    Simple API: Just give me the degrees.
    
    Returns: List of {degree_name, degree_level, url, confidence}
    """
    result = await extract_degrees_smart(domain)
    return result['degrees']


async def extract_degrees_with_stats(domain: str) -> Dict:
    """
    Detailed API: Give me degrees + extraction metadata.
    
    Returns: Full result dict with strategy info and timing
    """
    return await extract_degrees_smart(domain)


# ──────────────────────────────────────────────────────────────────────────────
# Test function
# ──────────────────────────────────────────────────────────────────────────────

async def test_smart_extractor():
    """Test on multiple universities with different structures."""
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    test_universities = [
        "mit.edu",       # Static catalog (easy)
        "stanford.edu",  # Likely dynamic
        "asu.edu",       # Large public university
        # "purdue.edu",  # Search interface (hardest) - skip for now
    ]
    
    for domain in test_universities:
        print("\n" + "="*80)
        print(f"TESTING: {domain.upper()}")
        print("="*80 + "\n")
        
        result = await extract_degrees_smart(domain, max_results=20)
        
        print(f"Strategy: {result['strategy_used']}")
        print(f"Time: {result['total_time_ms']}ms")
        print(f"Degrees found: {len(result['degrees'])}")
        
        if result['catalog_urls_tried']:
            print(f"\nCatalog URLs tried:")
            for url in result['catalog_urls_tried']:
                print(f"  - {url}")
        
        if result['degrees']:
            print(f"\nSample degrees (first 10):")
            for i, deg in enumerate(result['degrees'][:10], 1):
                print(f"{i:2d}. [{deg['degree_level']}] {deg['degree_name']}")
        else:
            print("\n[WARNING] No degrees extracted!")
        
        print()


if __name__ == "__main__":
    asyncio.run(test_smart_extractor())
