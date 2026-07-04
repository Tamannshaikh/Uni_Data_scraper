# services/jina_search.py
# Jina AI Search client for program discovery.
#
# Jina Search provides:
#   1. Web search results
#   2. Automatic page fetching
#   3. LLM-ready content formatting
#
# This replaces SerpAPI as the primary discovery engine.
#
# Strategy:
#   1. Search domain for graduate/program pages
#   2. Extract ALL URLs from Jina results
#   3. Program filters URLs (no AI)
#   4. Return ranked candidate URLs

import logging
import re
import urllib.parse
from typing import Optional, List
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

JINA_SEARCH_BASE = "https://s.jina.ai/"

# URL scoring patterns
CATALOG_PAGE_PATTERNS = [
    "/programs", "/programme", "/degrees", "/graduate", 
    "/postgraduate", "/masters", "/phd", "/doctoral",
    "/courses", "/study", "/catalog", "/academics", "/find"
]

# Patterns that indicate individual program pages (NOT catalogs)
INDIVIDUAL_PROGRAM_PATTERNS = [
    "master-of-", "bachelor-of-", "phd-in-", "doctor-of-",
    "mba-", "msc-", "ma-in-", "ms-in-", "graduate-diploma-in-",
    "graduate-certificate-in-", "executive-master-"
]

BAD_URL_PATTERNS = [
    "/news/", "/events/", "/research/", "/about/", "/admissions/",
    "/fees", "/tuition", "/funding", "/scholarships", "/faculty/",
    "/staff/", "/contact", "/library/", "/jobs/", "/careers/",
    "/alumni/", "/blog/", "/resources/", "/services/", "/facilities/"
]


def _score_url(url: str, domain: str) -> int:
    """
    Score a URL based on likelihood of being a program catalog page.
    
    Strategy:
    - University-wide catalogs (highest priority): +15 bonus
    - Catalog pages list MULTIPLE programs: positive scores
    - Individual program pages describe ONE program: negative scores
    - Non-program pages (news, events, etc.): negative scores
    
    Returns:
        Positive score = likely catalog/listing page
        Negative score = likely non-program page or individual program
        0 = neutral
    """
    score = 0
    url_lower = url.lower()
    path = urlparse(url).path.lower()
    parsed = urlparse(url_lower)
    subdomain = parsed.netloc.replace(f".{domain}", "").replace("www.", "")
    
    # Must be on the correct domain
    if domain.replace("www.", "") not in url_lower:
        return -100
    
    # HEAVY PENALTIES: Administrative/policy pages (NEVER catalog pages)
    PENALTY_PATTERNS = [
        "committee", "petition", "nomination", "reconstitution",
        "candidacy", "advancement", "constitution",
        "benefits", "policy", "policies", "forms",
        "requirements", "regulations", "handbook",
        "thesis", "dissertation",
        "faq", "help", "support",
    ]
    
    for pattern in PENALTY_PATTERNS:
        if pattern in path:
            return -20  # Heavy penalty - these are never catalogs
    
    # BONUS: University-wide catalog indicators (HIGHEST PRIORITY)
    # These are the main program directories that list ALL programs
    CENTRAL_CATALOG_INDICATORS = [
        # Subdomains
        ("grad.", 15),           # grad.university.edu
        ("graduate.", 15),       # graduate.university.edu
        ("catalog.", 12),        # catalog.university.edu
        ("degrees.", 12),        # degrees.university.edu
        # Path patterns that indicate centralized listings
        ("/programs-and-majors", 20),
        ("/all-programs", 20),
        ("/program-list", 20),
        ("/major-list", 20),
        ("/degree-search", 18),
        ("/find-compare-degree", 18),
        ("/degrees-and-programs", 18),
        ("/graduate-programs", 15),
        ("/degree-programs", 15),
        ("/masters-phd", 15),
        ("/postgraduate", 15),
        ("/academics/programs", 12),
        ("/academics/graduate", 12),
        # Simple but effective
        ("/programs/$", 20),     # /programs (exact, at end of path)
        ("/degrees/$", 20),      # /degrees (exact, at end of path)
    ]
    
    for indicator, bonus in CENTRAL_CATALOG_INDICATORS:
        if indicator.startswith("(") and indicator.endswith("."):
            # Subdomain check
            if subdomain.startswith(indicator.strip("()").strip(".")):
                score += bonus
                break
        elif indicator.endswith("$"):
            # End of path check (exact match)
            pattern = indicator.rstrip("$")
            if path == pattern or path == pattern + "/":
                score += bonus
                break
        elif indicator in path:
            # Path contains check
            score += bonus
            break
    
    # STRONG NEGATIVE: Individual program pages
    # These describe ONE program, not a catalog of programs
    for pattern in INDIVIDUAL_PROGRAM_PATTERNS:
        if pattern in path:
            score -= 10
    
    # Check for catalog page patterns (standard positive indicators)
    has_catalog_pattern = False
    for pattern in CATALOG_PAGE_PATTERNS:
        if pattern in path:
            has_catalog_pattern = True
            score += 3
    
    # Check for bad patterns
    for pattern in BAD_URL_PATTERNS:
        if pattern in path:
            score -= 5
    
    # Prefer shorter URLs (catalog pages are usually at top level)
    # /graduate/programs = good (depth 2)
    # /graduate/programs/master-of-cs = bad (depth 3, individual program)
    depth = path.count('/')
    if depth == 1 and has_catalog_pattern:
        # Very top level: /programs or /degrees
        score += 8
    elif depth == 2 and has_catalog_pattern:
        # Sweet spot: /graduate/programs or /study/courses
        score += 5
    elif depth == 3 and has_catalog_pattern:
        # Acceptable: /find/courses/graduate
        score += 2
    elif depth >= 4:
        # Too deep = likely individual program page or administrative page
        score -= 3
    
    return score


def extract_urls_from_jina_results(content: str, domain: str, verbose: bool = False) -> List[str]:
    """
    Extract and filter URLs from Jina search results.
    
    Args:
        content: Raw Jina search result text
        domain: University domain to filter by
        verbose: If True, print detailed scoring information
    
    Returns:
        List of scored and filtered URLs, best candidates first
    """
    # Extract all URLs from the content
    url_pattern = r'https?://[^\s\)\]\"\'\<\>]+'
    all_urls = re.findall(url_pattern, content)
    
    # Deduplicate
    seen = set()
    unique_urls = []
    for url in all_urls:
        # Clean up trailing punctuation
        url = url.rstrip('.,;:!?')
        
        # Normalize (remove fragments, trailing slashes)
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        
        if normalized not in seen:
            seen.add(normalized)
            unique_urls.append(normalized)
    
    # Score each URL
    scored_urls = [
        (url, _score_url(url, domain))
        for url in unique_urls
    ]
    
    # Filter: keep only URLs with positive scores
    filtered = [(url, score) for url, score in scored_urls if score > 0]
    
    # Sort by score (highest first)
    filtered.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(
        f"[jina_search] Extracted {len(unique_urls)} URLs, "
        f"filtered to {len(filtered)} candidates"
    )
    
    # VERBOSE: Print all scored URLs for diagnosis
    if verbose:
        print(f"\n{'='*80}")
        print(f"URL SCORING BREAKDOWN")
        print(f"{'='*80}")
        print(f"Total URLs extracted: {len(unique_urls)}")
        print(f"Positive scores (kept): {len(filtered)}")
        print(f"Negative/zero scores (rejected): {len(unique_urls) - len(filtered)}")
        print(f"\n{'='*80}")
        print(f"TOP 30 SCORED URLs:")
        print(f"{'='*80}\n")
        
        for i, (url, score) in enumerate(filtered[:30], 1):
            print(f"{i:2d}. [Score: {score:+3d}] {url}")
        
        if len(filtered) > 30:
            print(f"\n... and {len(filtered) - 30} more with positive scores")
        
        print(f"\n{'='*80}")
        print(f"REJECTED URLs (negative/zero scores):")
        print(f"{'='*80}\n")
        
        rejected = [(url, score) for url, score in scored_urls if score <= 0]
        rejected.sort(key=lambda x: x[1])
        
        for i, (url, score) in enumerate(rejected[:20], 1):
            print(f"{i:2d}. [Score: {score:+3d}] {url}")
        
        if len(rejected) > 20:
            print(f"\n... and {len(rejected) - 20} more rejected URLs")
        
        print(f"\n{'='*80}\n")
    
    # Return top URLs (without scores)
    return [url for url, score in filtered[:15]]


async def search_and_extract_catalog_urls(
    domain: str, 
    university_name: str, 
    api_key: Optional[str] = None,
    verbose: bool = False
) -> List[str]:
    """
    Use Jina AI Search to find program catalog URLs.
    
    Strategy:
    1. Search domain with multiple queries
    2. Extract all URLs from results
    3. Score and filter URLs programmatically
    4. Return top candidate URLs
    
    Args:
        domain: University domain (e.g., "unimelb.edu.au")
        university_name: Full university name
        api_key: Optional Jina AI API key for authentication
    
    Returns:
        List of candidate catalog URLs, ranked by score
    """
    queries = [
        f"site:{domain} graduate programs",
        f"site:{domain} graduate program directory",
        f"site:{domain} all graduate programs",
        f"site:{domain} master's programs catalog",
        f"site:{domain} postgraduate degrees",
        f"site:{domain} phd doctoral programs",
        f"site:{domain} degree programs listing",
        f"site:{domain} graduate catalog",
        f"site:{domain} fields of study graduate",
        f"site:{domain} areas of study graduate",
    ]
    
    all_content = []
    
    # Prepare headers
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    logger.info(f"[jina_search] Searching for program catalogs on {domain}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for query in queries:
            try:
                encoded_query = urllib.parse.quote(query)
                url = f"{JINA_SEARCH_BASE}{encoded_query}"
                
                logger.debug(f"[jina_search] Query: {query}")
                
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    content = response.text
                    all_content.append(content)
                    logger.info(f"[jina_search] Query succeeded: {len(content)} chars")
                elif response.status_code == 401:
                    logger.warning(f"[jina_search] Authentication required. Get a free API key at https://jina.ai/reader")
                    return []
                else:
                    logger.warning(f"[jina_search] Query failed: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.warning(f"[jina_search] Query failed: {type(e).__name__}: {e}")
                continue
    
    if not all_content:
        logger.warning(f"[jina_search] No results found for {domain}")
        return []
    
    # Combine all search results
    combined = "\n\n".join(all_content)
    logger.info(f"[jina_search] Total content: {len(combined)} chars from {len(all_content)} queries")
    
    # Extract and filter URLs programmatically (NO AI)
    candidate_urls = extract_urls_from_jina_results(combined, domain, verbose=verbose)
    
    if candidate_urls:
        logger.info(f"[jina_search] Returning {len(candidate_urls)} candidate URLs")
        for i, url in enumerate(candidate_urls[:5], 1):
            logger.info(f"[jina_search]   {i}. {url}")
    
    return candidate_urls
