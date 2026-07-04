"""
SIMPLE PIPELINE - Per-university extraction strategies

Architecture:
1. Check university config (UNIVERSITY_CONFIG.py)
2. If configured: use specified strategy for that university
3. If not: SerpAPI search fallback
4. Extract using appropriate strategy
5. Return {degree_name, url}

Strategies:
- anchor: Degree names in <a> tags
- list_text: Degree names in <li> text
- heading: Degree names in <h2>/<h3>
- heading_with_button: Degree in heading, link in button
- plain_text_list: Plain text, no individual URLs
- playwright_*: JavaScript-rendered (TODO)

No scoring. No confidence. No PageType. No LLM.
"""
import asyncio
import logging
from typing import List, Dict
import httpx

from UNIVERSITY_CONFIG import get_university_config, is_configured
from pipeline.extractors import extract_programs, deduplicate_programs

logger = logging.getLogger(__name__)


async def discover_programs(domain: str, max_results: int = 200) -> Dict:
    """
    Discover graduate programs for a university.
    
    Args:
        domain: University domain (e.g., "mit.edu")
        max_results: Maximum programs to return
    
    Returns:
        {
            'domain': str,
            'programs': List[{degree_name, url}],
            'source': 'manual_config' | 'serpapi_search',
            'strategy': str,
            'catalog_url': str | None,
            'time_sec': float
        }
    """
    import time
    start_time = time.time()
    
    result = {
        'domain': domain,
        'programs': [],
        'source': None,
        'strategy': None,
        'catalog_url': None,
        'time_sec': 0
    }
    
    # ═══════════════════════════════════════════════════════════════════
    # STEP 1: Check university config
    # ═══════════════════════════════════════════════════════════════════
    config = get_university_config(domain)
    
    if config:
        logger.info(f"[simple_pipeline] Using config for {domain}: strategy={config['strategy']}")
        result['source'] = 'manual_config'
        result['strategy'] = config['strategy']
        result['catalog_url'] = config['url']
        
        programs = await _extract_from_url(config['url'], config['strategy'])
        result['programs'] = programs[:max_results]
        result['time_sec'] = time.time() - start_time
        
        logger.info(f"[simple_pipeline] {domain}: {len(programs)} programs from {config['strategy']}")
        return result
    
    # ═══════════════════════════════════════════════════════════════════
    # STEP 2: SerpAPI search (fallback)
    # ═══════════════════════════════════════════════════════════════════
    logger.info(f"[simple_pipeline] No config for {domain}, using SerpAPI")
    result['source'] = 'serpapi_search'
    result['strategy'] = 'anchor'  # Default strategy for unknown universities
    
    from pipeline.searxng_client import search_degrees_searxng
    
    # Search queries
    queries = [
        f"site:{domain} graduate programs",
        f"site:{domain} master's programs",
        f"site:{domain} phd programs",
    ]
    
    all_results = []
    for query in queries:
        try:
            results = await search_degrees_searxng(domain, [query])
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"[simple_pipeline] Search failed for '{query}': {e}")
    
    if not all_results:
        logger.warning(f"[simple_pipeline] No search results for {domain}")
        result['time_sec'] = time.time() - start_time
        return result
    
    # Get unique URLs
    urls = list(dict.fromkeys([r.get('url') for r in all_results if r.get('url')]))
    
    # Take top 3
    top_urls = urls[:3]
    logger.info(f"[simple_pipeline] Fetching top {len(top_urls)} URLs for {domain}")
    
    # Extract from all URLs using default anchor strategy
    all_programs = []
    for url in top_urls:
        programs = await _extract_from_url(url, 'anchor')
        all_programs.extend(programs)
    
    # Deduplicate
    unique_programs = deduplicate_programs(all_programs)
    
    result['programs'] = unique_programs[:max_results]
    result['catalog_url'] = top_urls[0] if top_urls else None
    result['time_sec'] = time.time() - start_time
    
    logger.info(f"[simple_pipeline] {domain}: {len(unique_programs)} programs from SerpAPI")
    
    return result


async def _extract_from_url(url: str, strategy: str) -> List[Dict]:
    """
    Fetch a URL and extract programs using specified strategy.
    
    Args:
        url: URL to fetch
        strategy: Extraction strategy name
    
    Returns: 
        List of {degree_name, url}
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if resp.status_code != 200:
                logger.warning(f"[simple_pipeline] HTTP {resp.status_code} for {url[:60]}")
                return []
            
            # Debug logging
            logger.info(f"[simple_pipeline] Fetched {len(resp.text)} bytes from {url[:60]}")
            
            programs = extract_programs(strategy, str(resp.url), resp.text)
            return programs
    
    except Exception as e:
        logger.error(f"[simple_pipeline] Failed to fetch {url[:60]}: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════
# Test
# ═══════════════════════════════════════════════════════════════════════

async def test():
    """Test on known universities."""
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    test_domains = [
        "mit.edu",
        "purdue.edu",
        "uark.edu",
        "ucsd.edu",
    ]
    
    for domain in test_domains:
        print(f"\n{'='*80}")
        print(f"TESTING: {domain.upper()}")
        print('='*80 + "\n")
        
        result = await discover_programs(domain, max_results=50)
        
        print(f"Source: {result['source']}")
        print(f"Strategy: {result['strategy']}")
        print(f"Time: {result['time_sec']:.1f}s")
        print(f"Programs: {len(result['programs'])}")
        
        if result['programs']:
            print(f"\nFirst 20:")
            for i, prog in enumerate(result['programs'][:20], 1):
                print(f"  {i:2d}. {prog['degree_name'][:80]}")
        else:
            print("\n[WARNING] No programs found!")


if __name__ == "__main__":
    asyncio.run(test())
