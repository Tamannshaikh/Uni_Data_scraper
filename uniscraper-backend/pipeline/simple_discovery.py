# pipeline/simple_discovery.py
# Simplified program discovery: Jina Search → Catalog Pages → Extract Programs
#
# NO SerpAPI, NO OpenRouter, NO Firecrawl, NO complex AI reasoning
# Just: Find catalog pages → Fetch HTML → Extract program list

import asyncio
import logging
import re
from typing import List, Dict
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import httpx

from config import settings
from services.jina_search import search_and_extract_catalog_urls
from pipeline.known_catalogs import get_known_catalog_url, has_known_catalog

logger = logging.getLogger(__name__)


def _normalize_program_name(name: str) -> str:
    """Normalize program name for deduplication."""
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name.strip())
    # Remove common suffixes
    name = re.sub(r'\s*\(.*?\)\s*$', '', name)  # Remove (Online), (Full-time), etc.
    return name.lower()


def _clean_program_name(name: str) -> str:
    """
    Clean program name for display.
    
    Removes location/duration noise only. Does NOT try to fix duplicate prefixes
    since those should be handled at extraction time.
    """
    # Remove location/campus information
    name = re.sub(r'\b(Parkville|On Campus|Online)\b.*', '', name, flags=re.IGNORECASE)
    
    # Remove duration information
    name = re.sub(r'\b\d+\s+months?\b.*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\b\d+\s+years?\b.*', '', name, flags=re.IGNORECASE)
    
    # Remove credit points
    name = re.sub(r'\b\d+\s+credit points?\b.*', '', name, flags=re.IGNORECASE)
    
    # Remove course codes (e.g., GDA-BLTENV)
    name = re.sub(r'\b[A-Z]{2,4}-[A-Z0-9]+\b', '', name)
    
    # Remove "Graduate Coursework" type labels
    name = re.sub(r'\bGraduate Coursework\b', '', name, flags=re.IGNORECASE)
    
    # Clean up multiple spaces and trim
    name = ' '.join(name.split()).strip()
    
    return name


def _extract_programs_from_html(html: str, base_url: str) -> List[Dict]:
    """
    Extract program names and URLs from a catalog page HTML.
    
    SIMPLE STRATEGY:
    - Find all links on the page
    - Keep links where text contains degree keywords (master, phd, doctor)
    - Skip obvious junk (navigation, social media, etc.)
    - Return program list
    """
    programs = []
    
    # Skip social media domains
    SKIP_DOMAINS = [
        "youtube.com", "youtu.be", "facebook.com", "instagram.com",
        "linkedin.com", "twitter.com", "x.com", "vimeo.com"
    ]
    
    # Basic junk patterns to skip
    SKIP_PATTERNS = [
        'apply', 'admission', 'how to apply',
        'tuition', 'fees', 'scholarship', 'funding',
        'news', 'article', 'blog', 'event',
        'about', 'contact', 'careers',
        'faculty', 'staff', 'alumni',
        'terms', 'privacy', 'cookie',
        'learn more', 'read more', 'view all',
        'bachelor', 'undergraduate', 'accelerateDeg',
        'committee', 'petition', 'form',  # Administrative pages
        # Stronger junk filters
        'prospective students', 'prospective master', 'prospective doctor',
        'graduate and postdoctoral', 'postdoctoral services',
        'student handbook', 'office of', 'services',
        'financial aid', 'graduate studies', 'graduate education',
        'admissions office', 'graduate school office',
    ]
    
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        logger.debug(f"[simple_discovery] Found {len(links)} links on page")
        
        for link in links:
            href = link.get('href', '').strip()
            text = link.get_text(' ', strip=True)
            
            # Skip empty or very short text
            if not text or len(text) < 10:
                continue
            
            text_lower = text.lower()
            
            # STEP 1: Must contain degree keywords
            has_degree_keyword = (
                'master' in text_lower or 
                'phd' in text_lower or 
                'doctor' in text_lower or
                'mba' in text_lower
            )
            
            if not has_degree_keyword:
                continue
            
            # STEP 2: Skip junk patterns
            if any(pattern in text_lower or pattern in href.lower() for pattern in SKIP_PATTERNS):
                continue
            
            # Make absolute URL
            if href.startswith('/'):
                parsed_base = urlparse(base_url)
                abs_url = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
            elif href.startswith('http'):
                abs_url = href
            else:
                continue
            
            # Skip social media
            if any(domain in abs_url.lower() for domain in SKIP_DOMAINS):
                continue
            
            # Try to extract degree level from text
            degree_level = "Unspecified"
            if 'phd' in text_lower or 'doctor' in text_lower:
                degree_level = "PhD"
            elif 'master' in text_lower or 'mba' in text_lower:
                degree_level = "Master's"
            
            programs.append({
                "program_name": _clean_program_name(text.strip()),
                "degree_level": degree_level,
                "url": abs_url
            })
        
        logger.info(f"[simple_discovery] Extracted {len(programs)} programs from page")
        
    except Exception as e:
        logger.warning(f"[simple_discovery] Extraction error: {type(e).__name__}: {e}")
    
    return programs


async def discover_programs_simple(
    domain: str,
    university_name: str = "",
    max_catalog_pages: int = 10
) -> List[Dict]:
    """
    Simplified program discovery pipeline.
    
    Flow:
    1. Jina Search → Catalog URLs
    2. If too few results, try known fallback URLs
    3. Fetch each catalog page
    4. Extract programs from each page
    5. Deduplicate (keep version with URL if available)
    6. Return program list
    
    NO SerpAPI, NO OpenRouter, NO AI classification
    
    Args:
        domain: University domain
        university_name: University name (for Jina search)
        max_catalog_pages: Maximum catalog pages to crawl
    
    Returns:
        List of {"program_name", "degree_level", "url"}
    """
    logger.info(f"[simple_discovery] Starting simple discovery for {domain}")
    
    # Step 1: Check for known catalog URL (highest priority)
    catalog_urls = []
    
    if has_known_catalog(domain):
        known_url = get_known_catalog_url(domain)
        catalog_urls = [known_url]
        logger.info(
            f"[simple_discovery] Using known catalog URL for {domain}: {known_url}"
        )
    
    # Step 2: If no known URL or want to supplement, try Jina Search
    if not catalog_urls and settings.jina_api_key:
        logger.info(f"[simple_discovery] No known catalog, trying Jina Search for {domain}")
        catalog_urls = await search_and_extract_catalog_urls(
            domain,
            university_name,
            api_key=settings.jina_api_key
        )
    
    if not catalog_urls:
        logger.warning(f"[simple_discovery] No catalog URLs found for {domain}")
        return []
    
    # Limit to top N catalog pages
    catalog_urls = catalog_urls[:max_catalog_pages]
    
    logger.info(
        f"[simple_discovery] Processing {len(catalog_urls)} catalog pages"
    )
    
    # Step 2: Fetch and extract from each catalog page (CONCURRENTLY)
    async def fetch_and_extract(catalog_url: str, index: int) -> List[Dict]:
        """Fetch and extract programs from a single catalog page."""
        logger.info(f"[simple_discovery] [{index}/{len(catalog_urls)}] Fetching {catalog_url}")
        
        html = None
        
        try:
            # Try 1: HTTP fetch with realistic browser headers
            try:
                async with httpx.AsyncClient(
                    timeout=30.0,
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate, br",
                        "DNT": "1",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0",
                    }
                ) as client:
                    response = await client.get(catalog_url)
                    
                    if response.status_code == 200:
                        html = response.text
                        logger.debug(f"[simple_discovery] HTTP fetch successful: {len(html)} chars")
                    elif response.status_code == 403:
                        logger.info(f"[simple_discovery] 403 Forbidden - will try Jina Reader fallback")
                    else:
                        logger.warning(f"[simple_discovery] HTTP {response.status_code}")
                        
            except Exception as e:
                logger.debug(f"[simple_discovery] HTTP fetch failed: {type(e).__name__}: {e}")
            
            # Try 2: Jina Reader fallback for 403 or failed requests
            if not html and settings.jina_api_key:
                logger.info(f"[simple_discovery] Using Jina Reader fallback for {catalog_url}")
                
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        jina_url = f"https://r.jina.ai/{catalog_url}"
                        response = await client.get(
                            jina_url,
                            headers={"Authorization": f"Bearer {settings.jina_api_key}"}
                        )
                        
                        if response.status_code == 200:
                            # Jina Reader returns markdown-like text
                            content = response.text
                            
                            # Convert markdown links [text](url) to HTML <a href="url">text</a>
                            # so our HTML extractor can process it
                            import re
                            html = re.sub(
                                r'\[([^\]]+)\]\(([^\)]+)\)',
                                r'<a href="\2">\1</a>',
                                content
                            )
                            
                            logger.info(f"[simple_discovery] Jina Reader successful: {len(html)} chars")
                        elif response.status_code == 402:
                            logger.warning(f"[simple_discovery] Jina API rate limit (402)")
                        else:
                            logger.warning(f"[simple_discovery] Jina Reader failed: HTTP {response.status_code}")
                            
                except Exception as e:
                    logger.warning(f"[simple_discovery] Jina Reader error: {type(e).__name__}: {e}")
            
            # Check if we got usable content
            if not html or len(html) < 500:
                logger.warning(f"[simple_discovery] No usable content from {catalog_url}")
                return []
            
            # Extract programs
            programs = _extract_programs_from_html(html, catalog_url)
            
            logger.info(
                f"[simple_discovery] Extracted {len(programs)} programs from {catalog_url}"
            )
            
            return programs
            
        except Exception as e:
            logger.warning(
                f"[simple_discovery] Error processing {catalog_url}: {type(e).__name__}: {e}"
            )
            return []
    
    # Fetch all catalog pages concurrently
    results = await asyncio.gather(
        *[fetch_and_extract(url, i+1) for i, url in enumerate(catalog_urls)]
    )
    
    # Flatten results
    all_programs = []
    for programs in results:
        all_programs.extend(programs)
    
    logger.info(f"[simple_discovery] Total programs before deduplication: {len(all_programs)}")
    
    # Step 3: Deduplicate (keep version with URL if available)
    seen_names = {}
    
    for prog in all_programs:
        norm_name = _normalize_program_name(prog["program_name"])
        
        if norm_name in seen_names:
            # Already have this program - keep the one with URL
            existing = seen_names[norm_name]
            if not existing.get("url") and prog.get("url"):
                seen_names[norm_name] = prog  # Replace with version that has URL
        else:
            seen_names[norm_name] = prog
    
    unique_programs = list(seen_names.values())
    
    logger.info(f"[simple_discovery] After deduplication: {len(unique_programs)} unique programs")
    logger.info(f"[simple_discovery] Removed {len(all_programs) - len(unique_programs)} duplicates")
    
    # Step 4: Quality metrics
    with_url = sum(1 for p in unique_programs if p.get("url"))
    without_url = len(unique_programs) - with_url
    
    logger.info(
        f"[simple_discovery] Final: {len(unique_programs)} unique programs "
        f"(from {len(all_programs)} total)"
    )
    logger.info(
        f"[simple_discovery] Quality: {with_url} with URL, {without_url} without URL "
        f"({with_url * 100 // len(unique_programs) if unique_programs else 0}% coverage)"
    )
    
    # Log programs without URLs for debugging
    if without_url > 0:
        logger.warning(f"[simple_discovery] Programs without URLs:")
        for p in unique_programs[:10]:  # Show first 10
            if not p.get("url"):
                logger.warning(f"  - {p['program_name']}")
    
    return unique_programs
