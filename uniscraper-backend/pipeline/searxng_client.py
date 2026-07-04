"""
SearXNG Client - Unlimited Search Backend

HTML-only mode (JSON API has bot detection).
Connection cached after first success.
Parallel query execution for speed.

Usage:
    client = SearXNGClient()
    results = await client.search_parallel([query1, query2, query3])
"""
import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Default instances (public instances as fallback)
DEFAULT_SEARXNG_URLS = [
    "http://127.0.0.1:8080",  # Local Docker instance
    "http://localhost:8080",
    "https://search.inetol.net",  # Public instance 1
    "https://searx.be",  # Public instance 2
    "https://search.sapti.me",  # Public instance 3
]


class SearXNGClient:
    """Client for SearXNG metasearch engine (HTML mode only)."""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize with optional base URL."""
        self.base_url = base_url
        self._working_url = None  # Cached working instance
        self._instance_lock = asyncio.Lock()  # Prevent race condition in concurrent discovery
    
    async def _test_connection(self, url: str) -> bool:
        """Test if instance is accessible AND can return results."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test with a general query (site-specific queries often get blocked)
                resp = await client.get(
                    f"{url}/search",
                    params={"q": "python programming"},
                    headers=headers,
                    follow_redirects=True
                )
                
                if resp.status_code != 200:
                    return False
                
                # Verify we can actually get results
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                articles = soup.find_all('article', class_=lambda x: x and 'result' in x)
                
                # Must have at least 1 result to be considered working
                return len(articles) > 0
                
        except Exception:
            return False
    
    async def get_instance(self) -> Optional[str]:
        """Get working instance URL with double-checked locking to prevent race condition."""
        # First check without lock (fast path)
        if self._working_url:
            return self._working_url
        
        # Acquire lock for instance discovery
        async with self._instance_lock:
            # Re-check after acquiring lock (another coroutine may have set it)
            if self._working_url:
                return self._working_url
            
            # Only one coroutine reaches here - do the discovery
            urls = [self.base_url] if self.base_url else DEFAULT_SEARXNG_URLS
            
            logger.info(f"[searxng] Testing {len(urls)} instances...")
            for url in urls:
                logger.info(f"[searxng] Trying {url}...")
                if await self._test_connection(url):
                    self._working_url = url
                    logger.info(f"[searxng] [OK] Connected to {url}")
                    return url
                else:
                    logger.info(f"[searxng] [FAIL] {url} failed (no results or unreachable)")
            
            logger.warning("[searxng] No working instance found")
            return None
    
    async def search(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search using SearXNG HTML mode.
        
        Returns: List of {url, title, snippet}
        """
        instance = await self.get_instance()
        if not instance:
            logger.warning("[searxng] No working instance available")
            return []
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{instance}/search",
                    params={"q": query},
                    headers=headers,
                    follow_redirects=True
                )
                
                if resp.status_code != 200:
                    logger.warning(f"[searxng] HTTP {resp.status_code} for query: {query[:60]}")
                    return []
                
                # Parse HTML
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # SearXNG uses <article class="result ...">
                elements = soup.find_all('article', class_=lambda x: x and 'result' in x)
                
                results = []
                for elem in elements[:limit]:
                    try:
                        # Title is in <h3><a>...</a></h3>
                        h3 = elem.find('h3')
                        if not h3:
                            continue
                        
                        link = h3.find('a')
                        if not link:
                            continue
                        
                        title = link.get_text(strip=True)
                        url = link.get('href', '')
                        
                        # Snippet is in <p class="content">
                        content_elem = elem.find('p', class_='content')
                        snippet = content_elem.get_text(strip=True) if content_elem else ""
                        
                        if url and title:
                            results.append({"url": url, "title": title, "snippet": snippet})
                    except Exception as e:
                        logger.debug(f"[searxng] Error parsing result: {e}")
                        continue
                
                if results:
                    logger.debug(f"[searxng] Query returned {len(results)} results")
                else:
                    logger.debug(f"[searxng] Query returned 0 results (engines may be blocked)")
                
                return results
        
        except Exception as e:
            logger.error(f"[searxng] Search error for '{query[:60]}': {e}")
            return []
    
    async def search_parallel(self, queries: List[str], limit: int = 20) -> List[Dict]:
        """
        Execute multiple searches in parallel.
        
        Args:
            queries: List of search queries
            limit: Results per query
        
        Returns: Combined deduplicated results
        """
        # Execute all searches concurrently
        tasks = [self.search(q, limit) for q in queries]
        results_list = await asyncio.gather(*tasks)
        
        # Flatten and deduplicate
        seen = set()
        unique = []
        for results in results_list:
            for r in results:
                url = r["url"]
                if url not in seen:
                    seen.add(url)
                    unique.append(r)
        
        logger.info(f"[searxng] Parallel search: {len(queries)} queries → {len(unique)} unique results")
        return unique


async def search_degrees_searxng(domain: str, queries: List[str]) -> List[Dict]:
    """
    Search using SearXNG with parallel execution.
    
    Args:
        domain: University domain
        queries: List of queries
    
    Returns:
        Deduplicated results
    """
    # Use global singleton to preserve connection cache
    global _global_client
    if _global_client is None:
        _global_client = SearXNGClient()
    
    return await _global_client.search_parallel(queries, limit=20)


# Global singleton client (preserves connection cache across calls)
_global_client: Optional[SearXNGClient] = None


# Test function
async def test_searxng():
    """Test SearXNG connectivity and search."""
    print("\n" + "="*80)
    print("TESTING SEARXNG CONNECTION")
    print("="*80 + "\n")
    
    client = SearXNGClient()
    
    # Test connection
    instance = await client.get_instance()
    
    if not instance:
        print("[FAIL] No SearXNG instance available")
        print("\nTo set up local instance:")
        print("  docker run -d --name searxng -p 8080:8080 searxng/searxng")
        return
    
    print(f"[OK] Connected to: {instance}\n")
    
    # Test search
    print("Testing search: 'site:purdue.edu graduate catalog'")
    results = await client.search('site:purdue.edu "graduate catalog"', limit=5)
    
    print(f"\nFound {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['url']}")
        print()


if __name__ == "__main__":
    asyncio.run(test_searxng())
