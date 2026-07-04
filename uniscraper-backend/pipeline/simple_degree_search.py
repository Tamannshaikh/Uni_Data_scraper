"""
SIMPLIFIED DEGREE SEARCH - Search Engine Mode Only

NO CRAWLER. NO PAGE TAXONOMY. NO COMPLEXITY.

Strategy:
1. SerpAPI: Search for graduate degrees specifically
2. Filter: Keep only URLs with degree keywords
3. Extract: Get degree names from pages
4. Done.

For thousands of universities, this is the only feasible approach.
"""
import asyncio
import json
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path
import httpx

from config import settings

logger = logging.getLogger(__name__)

# ── CACHE CONFIGURATION ──────────────────────────────────────────────────────

# Cache directory for search results
CACHE_DIR = Path(__file__).parent.parent / "cache" / "degree_search"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cache TTL (30 days)
CACHE_TTL_DAYS = 30


# ── CACHE FUNCTIONS ──────────────────────────────────────────────────────────

def get_cache_path(domain: str) -> Path:
    """Get cache file path for a domain."""
    # Sanitize domain for filename
    safe_domain = domain.replace(".", "_").replace("/", "_")
    return CACHE_DIR / f"{safe_domain}.json"


def is_cache_expired(cache_path: Path) -> bool:
    """Check if cache file is expired (older than CACHE_TTL_DAYS)."""
    if not cache_path.exists():
        return True
    
    try:
        from datetime import datetime, timedelta
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        return age > timedelta(days=CACHE_TTL_DAYS)
    except Exception:
        return True


def load_from_cache(domain: str) -> Optional[List[Dict]]:
    """Load cached results for a domain if not expired."""
    cache_path = get_cache_path(domain)
    
    if not cache_path.exists():
        return None
    
    # Check expiry
    if is_cache_expired(cache_path):
        logger.info(f"[cache] Cache expired for {domain} (>{CACHE_TTL_DAYS} days old)")
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"[cache] ✓ Loaded {len(data)} degrees from cache for {domain}")
            return data
    except Exception as e:
        logger.warning(f"[cache] Error loading cache for {domain}: {e}")
        return None


def save_to_cache(domain: str, degrees: List[Dict]) -> None:
    """Save results to cache for a domain."""
    cache_path = get_cache_path(domain)
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(degrees, f, indent=2, ensure_ascii=False)
        logger.info(f"[cache] ✓ Saved {len(degrees)} degrees to cache for {domain}")
    except Exception as e:
        logger.error(f"[cache] Error saving cache for {domain}: {e}")


# ── DEGREE KEYWORDS (HARD REQUIREMENTS) ──────────────────────────────────────

DEGREE_KEYWORDS = [
    # Master's variants
    r'\bmaster\b', r'\bmaster of\b', r"master's\b",
    r'\bmsc\b', r'\bm\.?s\.?c?\b',
    r'\bma\b', r'\bm\.?a\.?\b',
    r'\bmba\b', r'\bm\.?b\.?a\.?\b',
    r'\bmeng\b', r'\bm\.?eng\.?\b',
    r'\bmph\b', r'\bmfa\b', r'\bmarch\b',
    r'\bllm\b', r'\bmres\b', r'\bmphil\b',
    
    # PhD variants
    r'\bphd\b', r'\bph\.?d\.?\b',
    r'\bdoctor of philosophy\b',
    r'\bdoctoral\b', r'\bdoctorate\b',
    
    # Other graduate
    r'\bgraduate certificate\b',
    r'\bpostgraduate\b',
]

# ── JUNK PATTERNS (HARD REJECTS) ─────────────────────────────────────────────

JUNK_PATTERNS = [
    # People/profiles
    r'\bfaculty\b', r'\bstaff\b', r'\bprofile\b', r'\bdirectory\b',
    r'\bpeople\b', r'\bprofessor\b', r'\binstructor\b',
    
    # Events/news
    r'\bnews\b', r'\bevent\b', r'\bblog\b', r'\bstory\b', r'\bstories\b',
    r'\bworkshop\b', r'\bseminar\b', r'\bconference\b', r'\bsymposium\b',
    
    # Non-degree programs
    r'\bfellowship\b', r'\bgrant\b', r'\bscholarship\b', r'\baward\b',
    r'\bsummer institute\b', r'\bsummer program\b', r'\bboot camp\b',
    r'\bresearch center\b', r'\bresearch institute\b',
    r'\binitiative\b', r'\bpartnership\b',
    
    # Admin pages
    r'\badmissions\b', r'\bapply\b', r'\bapplication\b',
    r'\bcontact\b', r'\babout\b', r'\bcalendar\b',
    r'\btuition\b', r'\bfees\b', r'\bfinancial aid\b',
]

# Generic title patterns (NOT specific degrees)
GENERIC_TITLE_PATTERNS = [
    'graduate concentrations',
    'graduate degree requirements',
    'graduate schools',
    'graduate programs',  # Too generic unless paired with specific degree
    'degree requirements',
    'overview',
    'curriculum',
    'admissions',
    'requirements',
    'options',
    'post-master',
    'engineering schools',
    'a purdue phd',  # Too generic
    'our phd programs',  # Landing page, not specific degree
]

# Negative URL patterns (strong rejects) - EXPANDED
BAD_URL_PATTERNS = [
    '/career',
    '/career-outcomes',
    '/outcomes',
    '/employment',
    '/salary',
    '/tuition',
    '/cost',
    '/admissions',
    '/apply',
    '/curriculum',
    '/requirements',
    '/faculty',
    '/about',
    '/overview',
    '/options',
    '/concentrations',
]

# Suffixes to remove from degree names
REMOVE_SUFFIXES = [
    "Career Outcomes",
    "Program",
    "Degree",
    "Curriculum",
    "Admissions",
    "Overview",
    "Requirements",
    "Summary",
    "Information",
    "Details",
]

# Stop words that indicate end of degree name (descriptive text starts)
STOP_WORDS = {
    "is",
    "are",
    "designed",
    "equips",
    "prepare",
    "prepares",
    "advance",
    "take",
    "read",
    "modality",
    "online",
    "learn",
    "harness",
    "for",
    "purdue",
    "build",
    "develop",
    "gain",
    "this",
    "offers",
    "provides",
    "helps",
    "allows",
    "students",
    "ready",
    "university",
    "explore",
    "discover",
    "a",
}

# Stop phrases to trim (more aggressive)
STOP_PHRASES = [
    "explore",
    "learn more",
    "learn",
    "discover",
    "designed",
    "prepare",
    "prepares",
    "equips",
    "advance",
    "advance your",
    "a flexible",
    "a fully",
    "the program",
    ", a",
]

# Stop boundaries (space-surrounded words that end degree names)
STOP_BOUNDARIES = [
    " is ",
    " are ",
    " designed ",
    " equips ",
    " prepare ",
    " prepares ",
    " offers ",
    " provides ",
    " help ",
    " helps ",
]

# Invalid trailing words (degree names shouldn't end with these)
INVALID_ENDINGS = [
    "and",
    "in",
    "&",
    "for",
    "of",
    "or",
    "with",
    "the",
    "a",
    "an",
]

# Maximum queries per university (budget protection)
MAX_QUERIES_PER_UNIVERSITY = 20

# ── SEARCH QUERIES ────────────────────────────────────────────────────────────

# Common academic fields for department-based queries (PRODUCTION LIST)
ACADEMIC_FIELDS = [
    # Computing
    "computer science", "software engineering", "cybersecurity",
    "data science", "artificial intelligence", "machine learning",
    "information systems", "information technology", "informatics",
    
    # Engineering
    "electrical engineering", "computer engineering", "mechanical engineering",
    "civil engineering", "chemical engineering", "industrial engineering",
    "systems engineering", "biomedical engineering", "materials science",
    "materials engineering", "environmental engineering", "aerospace engineering",
    "nuclear engineering", "petroleum engineering", "robotics",
    
    # Sciences
    "physics", "chemistry", "biology", "biochemistry",
    "mathematics", "statistics", "applied mathematics",
    "earth science", "geology", "geophysics", "environmental science",
    "microbiology", "genetics", "neuroscience",
    
    # Business
    "business", "finance", "accounting", "economics",
    "marketing", "management", "supply chain", "business analytics",
    "operations management", "entrepreneurship", "human resource management",
    
    # Health
    "public health", "nursing", "pharmacy", "medicine",
    "health administration", "nutrition", "epidemiology",
    "occupational therapy", "physical therapy", "speech pathology",
    
    # Social Sciences
    "psychology", "sociology", "political science", "international relations",
    "public policy", "public administration", "criminology", "anthropology",
    
    # Education
    "education", "curriculum and instruction", "higher education",
    "educational leadership", "special education",
    
    # Humanities
    "english", "history", "philosophy", "linguistics",
    "communication", "journalism",
    
    # Arts
    "art", "music", "fine arts", "design", "architecture", "theatre",
]


def build_catalog_queries(domain: str) -> List[str]:
    """
    Phase 0: Comprehensive catalog queries (HIGHEST YIELD).
    
    Target pages that list ALL programs (50-200 degrees per page).
    """
    return [
        f'site:{domain} "graduate catalog"',
        f'site:{domain} "programs of study"',
        f'site:{domain} "all graduate programs"',
        f'site:{domain} "graduate programs"',
        f'site:{domain} "degrees offered"',
        f'site:{domain} "all programs"',
        f'site:{domain} "masters programs"',
        f'site:{domain} "doctoral programs"',
        f'site:{domain} "graduate degrees"',
        f'site:{domain} "degree programs"',
    ]


def build_search_queries(domain: str) -> List[str]:
    """
    Phase 1: Broad degree searches (5 queries, not 10).
    
    Catalog queries moved to Phase 0.
    """
    return [
        f'site:{domain} "graduate programs"',
        f'site:{domain} "Master of"',
        f'site:{domain} "Doctor of Philosophy"',
        f'site:{domain} "PhD"',
        f'site:{domain} "MBA"',
    ]


def build_field_queries_phase2(domain: str) -> List[str]:
    """
    Phase 2: Top 10 academic fields (only run if Phase 1 yields < 30 degrees).
    """
    top_fields = [
        "computer science", "business", "electrical engineering",
        "mechanical engineering", "biology", "psychology",
        "economics", "education", "nursing", "public health",
    ]
    
    queries = []
    for field in top_fields:
        queries.append(f'site:{domain} "{field}" graduate')
    
    return queries


def build_field_queries_phase3(domain: str) -> List[str]:
    """
    Phase 3: Another 10 fields (only run if Phase 2 yields < 40 degrees).
    """
    more_fields = [
        "chemistry", "physics", "mathematics", "civil engineering",
        "chemical engineering", "finance", "accounting", "statistics",
        "data science", "biomedical engineering",
    ]
    
    queries = []
    for field in more_fields:
        queries.append(f'site:{domain} "{field}" graduate')
    
    return queries


async def search_degrees_serpapi(domain: str, queries: List[str] = None) -> List[Dict]:
    """
    Search for graduate degrees using SearXNG (unlimited), with SerpAPI/SearchAPI fallback.
    Returns list of {url, title, snippet}.
    
    Priority:
    1. SearXNG (unlimited, free, self-hosted or public)
    2. SerpAPI (if configured)
    3. SearchAPI (if configured)
    
    Args:
        domain: University domain (e.g., "purdue.edu")
        queries: Optional list of custom queries. If None, uses build_search_queries()
    """
    # Try SearXNG first (unlimited search)
    try:
        from pipeline.searxng_client import search_degrees_searxng
        logger.info("[search] Trying SearXNG (unlimited)...")
        results = await search_degrees_searxng(domain, queries or build_search_queries(domain))
        if results:
            logger.info(f"[search] ✓ SearXNG returned {len(results)} results")
            return results
        logger.warning("[search] SearXNG returned no results, trying paid APIs...")
    except Exception as e:
        logger.warning(f"[search] SearXNG failed: {e}, trying paid APIs...")
    
    # Fallback to SerpAPI
    if settings.serpapi_key:
        try:
            logger.info("[search] Trying SerpAPI...")
            return await _search_with_serpapi(domain, queries)
        except Exception as e:
            logger.warning(f"[search] SerpAPI failed: {e}, trying SearchAPI fallback")
    
    # Fallback to SearchAPI
    if hasattr(settings, 'searchapi_key') and settings.searchapi_key:
        try:
            logger.info("[search] Trying SearchAPI...")
            return await _search_with_searchapi(domain, queries)
        except Exception as e:
            logger.error(f"[search] SearchAPI also failed: {e}")
            return []
    
    logger.error("[search] No search backend available (SearXNG, SerpAPI, or SearchAPI)")
    return []


async def _search_with_serpapi(domain: str, queries: List[str] = None) -> List[Dict]:
    """Search using SerpAPI with provided queries."""
    if queries is None:
        queries = build_search_queries(domain)
    
    all_results = []
    failed_count = 0
    
    for query in queries:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": settings.serpapi_key,
                        "num": 20,
                        "engine": "google",
                    }
                )
                
                if resp.status_code == 403:
                    failed_count += 1
                    logger.warning(f"[serpapi] 403 rate limit hit on query {failed_count}")
                    # If we hit 3+ rate limits in a row, bail out and try SearchAPI
                    if failed_count >= 3:
                        raise Exception("SerpAPI rate limit exhausted")
                    continue
                    
                if resp.status_code != 200:
                    logger.warning(f"[serpapi] {resp.status_code} for query: {query}")
                    continue
                
                # Reset failed count on success
                failed_count = 0
                
                data = resp.json()
                organic = data.get("organic_results", [])
                
                for result in organic:
                    all_results.append({
                        "url": result.get("link", ""),
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                    })
                
                logger.info(f"[serpapi] Query '{query[:60]}...' returned {len(organic)} results")
        
        except Exception as e:
            logger.error(f"[serpapi] Error searching '{query}': {e}")
            # Re-raise to trigger fallback
            raise
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for r in all_results:
        url = r["url"]
        if url not in seen:
            seen.add(url)
            unique.append(r)
    
    logger.info(f"[serpapi] Total unique results: {len(unique)}")
    return unique


async def _search_with_searchapi(domain: str, queries: List[str] = None) -> List[Dict]:
    """Search using SearchAPI (fallback) with provided queries."""
    if queries is None:
        queries = build_search_queries(domain)
    
    all_results = []
    
    for query in queries:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={
                        "q": query,
                        "api_key": settings.searchapi_key,
                        "engine": "google",
                        "num": 20,
                    }
                )
                
                if resp.status_code != 200:
                    logger.warning(f"[searchapi] {resp.status_code} for query: {query}")
                    continue
                
                data = resp.json()
                organic = data.get("organic_results", [])
                
                for result in organic:
                    all_results.append({
                        "url": result.get("link", ""),
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                    })
                
                logger.info(f"[searchapi] Query '{query[:60]}...' returned {len(organic)} results")
        
        except Exception as e:
            logger.error(f"[searchapi] Error searching '{query}': {e}")
            continue
    
    # Deduplicate by URL
    seen = set()
    unique = []
    for r in all_results:
        url = r["url"]
        if url not in seen:
            seen.add(url)
            unique.append(r)
    
    logger.info(f"[searchapi] Total unique results: {len(unique)}")
    return unique


def has_degree_keyword(text: str) -> bool:
    """Check if text contains any degree keyword."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in DEGREE_KEYWORDS)


def has_junk_pattern(text: str) -> bool:
    """Check if text contains any junk pattern."""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in JUNK_PATTERNS)


def trim_degree_name(name: str) -> str:
    """
    Trim degree name at stop-word boundaries using aggressive phrase and token detection.
    
    Stops at descriptive text like "designed for", "explore", ", a", etc.
    
    Examples:
    - "Master of Science in Engineering Technology, a flexible program" 
      → "Master of Science in Engineering Technology"
    - "Master of Science in Mechanical Engineering Explore"
      → "Master of Science in Mechanical Engineering"
    - "Master of Science in Communication is designed"
      → "Master of Science in Communication"
    """
    if not name:
        return name
    
    # First check stop phrases (longer patterns)
    lower = name.lower()
    for phrase in STOP_PHRASES:
        idx = lower.find(phrase)
        if idx != -1:
            name = name[:idx].strip()
            lower = name.lower()  # Update for next iteration
    
    # Then check stop boundaries (space-surrounded phrases)
    for boundary in STOP_BOUNDARIES:
        idx = lower.find(boundary)
        if idx != -1:
            name = name[:idx].strip()
            lower = name.lower()
    
    # Token-based stop word detection (most aggressive)
    tokens = name.split()
    clean_tokens = []
    
    for token in tokens:
        token_lower = token.lower().strip(".,;:")
        # Stop at any stop word
        if token_lower in STOP_WORDS:
            break
        clean_tokens.append(token)
    
    name = " ".join(clean_tokens)
    
    # Clean up trailing punctuation and whitespace
    name = name.strip(" -,:;.")
    
    # Remove invalid trailing words
    words = name.split()
    while words and words[-1].lower() in INVALID_ENDINGS:
        words.pop()
    
    name = " ".join(words)
    
    return name


def is_valid_degree_length(name: str) -> bool:
    """
    Check if degree name length is reasonable.
    
    Real degree names are typically 4-12 words.
    Reject suspiciously long names (likely extraction errors).
    """
    word_count = len(name.split())
    char_count = len(name)
    
    # Too short
    if word_count < 3 or char_count < 10:
        return False
    
    # Too long (likely captured descriptive text)
    if word_count > 15 or char_count > 120:
        return False
    
    return True


def clean_degree_name(name: str) -> str:
    """
    Clean junk suffixes from degree names.
    
    Examples:
    - "Master of Science in Finance Career Outcomes" → "Master of Science in Finance"
    - "Doctor of Philosophy in Program" → "Doctor of Philosophy"
    - "MS in Computer Science Degree" → "MS in Computer Science"
    """
    if not name:
        return name
    
    # First trim at stop words
    name = trim_degree_name(name)
    
    # Then remove trailing suffixes
    for suffix in REMOVE_SUFFIXES:
        # Match suffix at word boundary, followed by anything
        name = re.sub(rf'\b{suffix}\b.*$', '', name, flags=re.I).strip()
    
    # Remove trailing "in" if it's at the end
    name = re.sub(r'\bin\s*$', '', name, flags=re.I).strip()
    
    return name


def score_url(url: str, title: str) -> int:
    """
    Score a search result based on URL and title patterns.
    Higher score = more likely to be a degree page.
    
    IMPROVED: Lowered threshold to 3 for better recall.
    
    Returns score (keep if >= 3).
    """
    score = 0
    url_lower = url.lower()
    title_lower = title.lower()
    
    # Check for generic titles first (hard reject)
    for pattern in GENERIC_TITLE_PATTERNS:
        if pattern in title_lower:
            return -100  # Immediate rejection
    
    # POSITIVE signals - graduate program indicators
    if '/graduate/' in url_lower:
        score += 5
    if '/program/' in url_lower or '/programme/' in url_lower:
        score += 5
    if '/degree/' in url_lower or '/degrees/' in url_lower:
        score += 5
    if '/masters/' in url_lower or '/master/' in url_lower:
        score += 5
    if '/phd/' in url_lower or '/doctoral/' in url_lower:
        score += 5
    if '/mba/' in url_lower:
        score += 5
    if '/academics/' in url_lower:
        score += 3
    if '/online/program/' in url_lower:
        score += 5
    if '/programs/' in url_lower:
        score += 5
    if '/catalog/' in url_lower:
        score += 3
    
    # NEGATIVE signals - non-degree pages (STRONGER PENALTIES + BAD PATTERNS)
    for pattern in BAD_URL_PATTERNS:
        if pattern in url_lower:
            score -= 20
    
    if '/news/' in url_lower:
        score -= 15
    if '/blog/' in url_lower:
        score -= 15
    if '/faculty/' in url_lower or '/staff/' in url_lower:
        score -= 15
    if '/research/' in url_lower and '/programs/' not in url_lower:
        score -= 15
    if '/theses/' in url_lower or '/thesis/' in url_lower:
        score -= 20
    if '/dissertation/' in url_lower:
        score -= 20
    if '/archive/' in url_lower or '/archives/' in url_lower:
        score -= 20
    if '/people/' in url_lower or '/directory/' in url_lower:
        score -= 15
    if '/event/' in url_lower:
        score -= 15
    if 'docs.lib.' in url_lower or 'digitalcommons.' in url_lower:
        score -= 25  # Thesis repositories
    if 'historicalnewspapers.' in url_lower:
        score -= 25
    
    return score


def filter_degree_pages(results: List[Dict]) -> List[Dict]:
    """
    Filter search results to keep only graduate degree pages.
    
    IMPROVED: Lowered threshold to score >= 3 for better recall.
    
    Rules:
    1. MUST have degree keyword in URL, title, or snippet
    2. MUST NOT have junk pattern in URL or title
    3. URL score must be >= 3
    """
    filtered = []
    
    for result in results:
        url = result["url"]
        title = result["title"]
        snippet = result["snippet"]
        
        # Combine for checking
        combined = f"{url} {title} {snippet}"
        
        # Must have degree keyword
        if not has_degree_keyword(combined):
            logger.debug(f"[simple_search] REJECT (no degree keyword): {url[:80]}")
            continue
        
        # Must not have junk
        if has_junk_pattern(f"{url} {title}"):
            logger.debug(f"[simple_search] REJECT (junk pattern): {title[:60]}")
            continue
        
        # Score URL
        url_score = score_url(url, title)
        if url_score < 3:
            logger.debug(f"[simple_search] REJECT (low score {url_score}): {url[:80]}")
            continue
        
        result["score"] = url_score
        filtered.append(result)
    
    # Sort by score (highest first)
    filtered.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    logger.info(f"[simple_search] Filtered: {len(filtered)}/{len(results)} passed (score >= 3)")
    return filtered


async def extract_degree_names(pages: List[Dict]) -> List[Dict]:
    """
    Extract degree names from filtered pages using Gemini.
    
    IMPROVED: 
    - Uses title + snippet only (no page fetch needed!)
    - Strict prompt focusing on formal academic degrees
    - Faster and cheaper
    """
    if not settings.gemini_api_key or not pages:
        return []
    
    # Build extraction data from title + snippet (no fetch needed!)
    pages_data = []
    for i, p in enumerate(pages):
        pages_data.append({
            "index": i,
            "title": p["title"],
            "snippet": p["snippet"][:200],  # Limit snippet length
            "url": p["url"]
        })
    
    prompt = f"""You are extracting university graduate DEGREE PROGRAMS.

Extract ONLY formal academic degrees.

VALID examples:
- MS in Computer Science
- Master of Business Administration
- MA in Economics
- PhD in Physics
- MEng in Mechanical Engineering
- Graduate Certificate in Data Science
- Doctor of Education
- Master of Public Health

DO NOT extract:
- courses or classes
- departments or schools
- faculty profiles
- theses or dissertations
- workshops or camps
- fellowships or grants
- research centers or institutes
- blog posts or news articles
- admissions pages
- events or seminars

Return ONLY degree programs that award an academic credential.

For each valid degree, return:
- index: the result number
- degree_name: full degree name
- level: one of "Master's", "Doctoral", "Certificate", "MBA"

Return [] if no degree exists.

Results to analyze:
{json.dumps(pages_data, indent=2)}

Return JSON array: [{{"index": 0, "degree_name": "...", "level": "..."}}, ...]
"""
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            
            if resp.status_code != 200:
                logger.error(f"[simple_search] Gemini {resp.status_code}")
                return []
            
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            extractions = json.loads(content)
            
            # Map back to URLs
            results = []
            for ext in extractions:
                idx = ext.get("index")
                if idx is not None and idx < len(pages):
                    results.append({
                        "program_name": ext.get("degree_name", ""),
                        "degree_level": ext.get("level", "Unspecified"),
                        "url": pages[idx]["url"],
                        "confidence": 0.9,
                    })
            
            logger.info(f"[simple_search] Extracted {len(results)} degrees from {len(pages)} pages")
            return results
    
    except Exception as e:
        logger.error(f"[simple_search] Extraction error: {e}")
        return []


async def deduplicate_degrees(degrees: List[Dict]) -> List[Dict]:
    """
    Deduplicate and standardize degree names using Gemini.
    
    Example:
    - "MS in Computer Science"
    - "Master of Science in Computer Science"
    → "Master of Science in Computer Science"
    """
    if not degrees or not settings.gemini_api_key:
        return degrees
    
    # Extract just the names for deduplication
    degree_names = [
        {"index": i, "name": d["program_name"], "url": d["url"]}
        for i, d in enumerate(degrees)
    ]
    
    prompt = f"""You are given a list of university degree names.

Merge duplicates and standardize naming.

Rules:
1. Expand abbreviations to full names when possible
   - "MS in Computer Science" → "Master of Science in Computer Science"
   - "PhD in Biology" → "Doctor of Philosophy in Biology"
   - "MBA" → "Master of Business Administration"

2. Merge duplicates:
   - "MS in CS" and "Master of Science in Computer Science" → keep one
   
3. For each unique degree, return the BEST (most complete) name and the original index

Examples:
Input: [
  {{"index": 0, "name": "MS in Computer Science"}},
  {{"index": 1, "name": "Master of Science in Computer Science"}},
  {{"index": 2, "name": "MBA"}}
]
Output: [
  {{"index": 1, "standardized_name": "Master of Science in Computer Science"}},
  {{"index": 2, "standardized_name": "Master of Business Administration"}}
]

Degrees to deduplicate:
{json.dumps(degree_names, indent=2)}

Return JSON array of unique degrees with their original index.
"""
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={settings.gemini_api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            
            if resp.status_code != 200:
                logger.warning(f"[simple_search] Deduplication failed: Gemini {resp.status_code}")
                return degrees
            
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            
            unique_indices = json.loads(content)
            
            # Map back to original degrees
            unique_degrees = []
            for item in unique_indices:
                idx = item.get("index")
                standardized_name = item.get("standardized_name")
                
                if idx is not None and idx < len(degrees):
                    degree = degrees[idx].copy()
                    if standardized_name:
                        degree["program_name"] = standardized_name
                    unique_degrees.append(degree)
            
            logger.info(
                f"[simple_search] Deduplicated: {len(degrees)} → {len(unique_degrees)} "
                f"({len(degrees) - len(unique_degrees)} duplicates removed)"
            )
            return unique_degrees
    
    except Exception as e:
        logger.warning(f"[simple_search] Deduplication error: {e}, returning original list")
        return degrees


def validate_extracted_degree(name: str) -> tuple[bool, str]:
    """
    Validate that extracted string is actually a clean degree name.
    
    Filters out:
    - Text that's too long (grabbed surrounding context)
    - Contains junk keywords (student, faculty, etc.)
    - Ends with junk words (students, and, etc.)
    - Suspiciously short/incomplete
    
    Returns: (is_valid, reason_if_invalid)
    """
    if not name:
        return False, "EMPTY"
    
    # Too long - likely grabbed surrounding text
    word_count = len(name.split())
    if word_count > 12:
        return False, "TOO_LONG"
    
    # Too short - incomplete extraction
    if len(name) < 5:
        return False, "TOO_SHORT"
    
    # Contains junk keywords that indicate it's not a degree name
    junk_keywords = [
        "student", "students", "faculty", "staff",
        "curriculum", "requirements", "admissions", "application",
        "program prepares", "coursework", "designed for",
        "explore", "learn more", "click here", "read more",
        "deadline", "tuition", "apply now", "information"
    ]
    
    lower = name.lower()
    for keyword in junk_keywords:
        if keyword in lower:
            return False, f"JUNK_KEYWORD:{keyword}"
    
    # Ends with junk (bad truncation)
    bad_endings = [
        "students", "faculty", "program", "curriculum", 
        "and", "or", "with", "for", "the", "a", "an"
    ]
    for ending in bad_endings:
        if name.lower().endswith(ending):
            return False, f"BAD_ENDING:{ending}"
    
    # Contains multiple degrees mashed together (regex over-match)
    degree_count = sum([
        "master" in lower,
        "doctor" in lower or "phd" in lower,
        lower.count("m.s."),
        lower.count("m.a."),
        lower.count("ph.d.")
    ])
    if degree_count > 1:
        return False, "MULTIPLE_DEGREES"
    
    return True, "OK"


def extract_degree_from_title_regex(title: str) -> tuple[str, str]:
    """
    Extract degree name directly from title using regex patterns.
    
    IMPROVED: Added dotted abbreviations and more comprehensive patterns.
    
    Returns (degree_name, degree_level) or (None, None) if no match.
    """
    # Degree extraction patterns (capture the full degree name)
    DEGREE_EXTRACTION_PATTERNS = [
        # Master of X in Y
        (r'(Master of Science in [^-|]+)', "Master's"),
        (r'(Master of Arts in [^-|]+)', "Master's"),
        (r'(Master of Engineering in [^-|]+)', "Master's"),
        (r'(Master of Business Administration)', "MBA"),
        (r'(Master of Public Health)', "Master's"),
        (r'(Master of Fine Arts)', "Master's"),
        (r'(Master of Education)', "Master's"),
        (r'(Master of Architecture)', "Master's"),
        (r'(Master of Public Policy)', "Master's"),
        (r'(Master of Accounting)', "Master's"),
        (r'(Master of Social Work)', "Master's"),
        
        # Dotted abbreviations (M.S., M.A., etc.)
        (r'(M\.S\. in [^-|]+)', "Master's"),
        (r'(M\.Sc\. in [^-|]+)', "Master's"),
        (r'(M\.A\. in [^-|]+)', "Master's"),
        (r'(M\.Eng\. in [^-|]+)', "Master's"),
        (r'(M\.S\.E\. in [^-|]+)', "Master's"),
        (r'(M\.B\.A\. in [^-|]+)', "MBA"),
        (r'(M\.P\.H\. in [^-|]+)', "Master's"),
        (r'(M\.F\.A\. in [^-|]+)', "Master's"),
        (r'(M\.Ed\. in [^-|]+)', "Master's"),
        (r'(M\.Arch\. in [^-|]+)', "Master's"),
        (r'(M\.P\.P\. in [^-|]+)', "Master's"),
        (r'(M\.Acc\. in [^-|]+)', "Master's"),
        (r'(M\.S\.W\. in [^-|]+)', "Master's"),
        
        # Non-dotted abbreviations
        (r'(MS in [^-|]+)', "Master's"),
        (r'(MSc in [^-|]+)', "Master's"),
        (r'(MA in [^-|]+)', "Master's"),
        (r'(MEng in [^-|]+)', "Master's"),
        (r'(MSE in [^-|]+)', "Master's"),
        (r'(MBA in [^-|]+)', "MBA"),
        (r'(MPH in [^-|]+)', "Master's"),
        (r'(MFA in [^-|]+)', "Master's"),
        (r'(MEd in [^-|]+)', "Master's"),
        (r'(MArch in [^-|]+)', "Master's"),
        (r'(MPP in [^-|]+)', "Master's"),
        (r'(MAcc in [^-|]+)', "Master's"),
        (r'(MSW in [^-|]+)', "Master's"),
        
        # PhD/Doctoral with dots
        (r'(Ph\.D\. in [^-|]+)', "PhD"),
        (r'(Doctor of Philosophy in [^-|]+)', "PhD"),
        (r'(PhD in [^-|]+)', "PhD"),
        (r'(Doctor of Education)', "Doctoral"),
        (r'(Doctor of Nursing Practice)', "Doctoral"),
        (r'(Doctor of Psychology)', "Doctoral"),
        (r'(D\.N\.P\.)', "Doctoral"),
        (r'(DNP)', "Doctoral"),
        (r'(Ed\.D\. in [^-|]+)', "Doctoral"),
        (r'(Psy\.D\. in [^-|]+)', "Doctoral"),
        
        # Combined degrees (B.S./M.S., etc.)
        (r'(B\.S\./M\.S\. in [^-|]+)', "Master's"),
        (r'(BS/MS in [^-|]+)', "Master's"),
        
        # Graduate certificates
        (r'(Graduate Certificate in [^-|]+)', "Certificate"),
        
        # Standalone degrees
        (r'\b(M\.B\.A\.)\b', "MBA"),
        (r'\b(MBA)\b', "MBA"),
        (r'\b(M\.S\.)\b', "Master's"),
        (r'\b(M\.A\.)\b', "Master's"),
        
        # Generic fallbacks (last resort)
        (r'(M\.?S\.? [A-Z][^-|]+)', "Master's"),
        (r'(Ph\.?D\.? [A-Z][^-|]+)', "PhD"),
    ]
    
    for pattern, level in DEGREE_EXTRACTION_PATTERNS:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            degree_name = match.group(1).strip()
            # Clean up common junk
            degree_name = re.sub(r'\s+[-|].*$', '', degree_name)  # Remove " - University"
            degree_name = re.sub(r'\s+\(.*?\)$', '', degree_name)  # Remove " (MSENE)"
            degree_name = degree_name.strip()
            
            # Validate before returning
            is_valid, reason = validate_extracted_degree(degree_name)
            if is_valid and len(degree_name) > 5:  # Reasonable length
                return (degree_name, level)
            elif not is_valid:
                logger.debug(f"[regex] Rejected '{degree_name[:60]}...' - {reason}")
    
    return (None, None)


def normalize_degree_name(name: str) -> str:
    """
    Normalize degree names for consistent formatting and deduplication.
    
    Examples:
    - "M.S. in Computer Science" → "Master of Science in Computer Science"
    - "MS Computer Science" → "Master of Science in Computer Science"
    - "PhD in Biology" → "Doctor of Philosophy in Biology"
    - "MBA" → "Master of Business Administration"
    """
    if not name:
        return name
    
    # First, clean junk suffixes
    name = clean_degree_name(name)
    
    # Remove trailing separators (university names appended)
    for sep in [' - ', ' | ', ' : ', ' — ']:
        if sep in name:
            name = name.split(sep)[0].strip()
            break
    
    # Remove dots from abbreviations
    name = re.sub(r'\.', '', name)
    
    # Standardize common abbreviations using regex
    # IMPORTANT: Handle both "MS in X" and "MS X" patterns
    
    # MS/MSc variants (add "in" if missing)
    name = re.sub(r'^MS\s+(?!in\s)(.+)$', r'Master of Science in \1', name, flags=re.I)
    name = re.sub(r'^MS\s+in\s+(.+)$', r'Master of Science in \1', name, flags=re.I)
    name = re.sub(r'^MSc\s+(?!in\s)(.+)$', r'Master of Science in \1', name, flags=re.I)
    name = re.sub(r'^MSc\s+in\s+(.+)$', r'Master of Science in \1', name, flags=re.I)
    
    # MA variants
    name = re.sub(r'^MA\s+(?!in\s)(.+)$', r'Master of Arts in \1', name, flags=re.I)
    name = re.sub(r'^MA\s+in\s+(.+)$', r'Master of Arts in \1', name, flags=re.I)
    
    # MEng variants
    name = re.sub(r'^MEng\s+(?!in\s)(.+)$', r'Master of Engineering in \1', name, flags=re.I)
    name = re.sub(r'^MEng\s+in\s+(.+)$', r'Master of Engineering in \1', name, flags=re.I)
    
    # MPH variants
    name = re.sub(r'^MPH\s+(?!in\s)(.+)$', r'Master of Public Health in \1', name, flags=re.I)
    name = re.sub(r'^MPH\s+in\s+(.+)$', r'Master of Public Health in \1', name, flags=re.I)
    
    # MFA variants
    name = re.sub(r'^MFA\s+(?!in\s)(.+)$', r'Master of Fine Arts in \1', name, flags=re.I)
    name = re.sub(r'^MFA\s+in\s+(.+)$', r'Master of Fine Arts in \1', name, flags=re.I)
    
    # MEd variants
    name = re.sub(r'^MEd\s+(?!in\s)(.+)$', r'Master of Education in \1', name, flags=re.I)
    name = re.sub(r'^MEd\s+in\s+(.+)$', r'Master of Education in \1', name, flags=re.I)
    
    # PhD variants
    name = re.sub(r'^PhD\s+(?!in\s)(.+)$', r'Doctor of Philosophy in \1', name, flags=re.I)
    name = re.sub(r'^PhD\s+in\s+(.+)$', r'Doctor of Philosophy in \1', name, flags=re.I)
    name = re.sub(r'^PhDin\s+(.+)$', r'Doctor of Philosophy in \1', name, flags=re.I)
    
    # DNP variants
    name = re.sub(r'^DNP$', 'Doctor of Nursing Practice', name, flags=re.I)
    name = re.sub(r'^DNP\s+(?!in\s)(.+)$', r'Doctor of Nursing Practice in \1', name, flags=re.I)
    
    # EdD variants
    name = re.sub(r'^EdD\s+(?!in\s)(.+)$', r'Doctor of Education in \1', name, flags=re.I)
    name = re.sub(r'^EdD\s+in\s+(.+)$', r'Doctor of Education in \1', name, flags=re.I)
    
    # Standalone MBA
    name = re.sub(r'^MBA$', 'Master of Business Administration', name, flags=re.I)
    name = re.sub(r'^MBA\s+(?!in\s)(.+)$', r'Master of Business Administration in \1', name, flags=re.I)
    
    # Clean up extra whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def get_dedup_key(name: str) -> str:
    """
    Generate canonical deduplication key using aggressive normalization.
    
    Strategy:
    - Master of Science → ms
    - Master's → ms
    - Master of Arts → ma
    - Doctor of Philosophy → phd
    - Remove all punctuation and spaces
    
    Examples:
    - "Master of Science in Computer Science" → "msincomputerscience"
    - "MS in Computer Science" → "msincomputerscience"
    - "Master's in Computer Science" → "msincomputerscience"
    - (same key, will be deduplicated)
    """
    # Normalize to lowercase
    key = name.lower()
    
    # Aggressive abbreviation normalization
    key = re.sub(r'\bmaster of science\b', 'ms', key)
    key = re.sub(r"\bmaster's\b", 'ms', key)
    key = re.sub(r'\bmaster of arts\b', 'ma', key)
    key = re.sub(r'\bmaster of engineering\b', 'meng', key)
    key = re.sub(r'\bmaster of business administration\b', 'mba', key)
    key = re.sub(r'\bmaster of public health\b', 'mph', key)
    key = re.sub(r'\bmaster of fine arts\b', 'mfa', key)
    key = re.sub(r'\bmaster of education\b', 'med', key)
    key = re.sub(r'\bmaster of architecture\b', 'march', key)
    key = re.sub(r'\bdoctor of philosophy\b', 'phd', key)
    key = re.sub(r'\bdoctor of education\b', 'edd', key)
    key = re.sub(r'\bdoctor of nursing practice\b', 'dnp', key)
    
    # Remove all non-alphanumeric
    key = re.sub(r'[^a-z0-9]', '', key)
    
    return key


async def mine_catalog_page(url: str) -> List[tuple]:
    """
    Fetch a catalog page and extract all degree names using regex.
    
    NO CRAWLER. Just fetch 1-2 key catalog pages and regex extract.
    
    Returns list of (degree_name, degree_level) tuples.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            
            if resp.status_code != 200:
                return []
            
            html = resp.text
            
            # Extract all degree mentions from HTML text
            # Remove HTML tags for cleaner extraction
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            
            degrees = []
            seen = set()  # Deduplicate within same page
            
            # IMPROVED: Stricter regex patterns with better boundaries
            
            # Master of X in Y patterns (capture just the degree name)
            for match in re.finditer(
                r'Master of Science in ([A-Z][A-Za-z\s,&-]{8,50})(?:\s+(?:Advance|Designed|Purdue|This|Read|Harness|Build|Equips|Learn|Gain|Develop|Take)|\.|$)',
                text,
                re.IGNORECASE
            ):
                field = match.group(1).strip()
                # Remove trailing junk like "Advance your career"
                field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                if field and len(field) > 5 and field not in seen:
                    degree_name = f"Master of Science in {field}"
                    degrees.append((degree_name, "Master's"))
                    seen.add(field)
            
            for match in re.finditer(
                r'Master of Arts in ([A-Z][A-Za-z\s,&-]{8,50})(?:\s+(?:Advance|Designed|Purdue|This|Read|Harness|Build|Equips)|\.|$)',
                text,
                re.IGNORECASE
            ):
                field = match.group(1).strip()
                field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                if field and len(field) > 5 and field not in seen:
                    degree_name = f"Master of Arts in {field}"
                    degrees.append((degree_name, "Master's"))
                    seen.add(field)
            
            # Other Master of X patterns
            for master_type in ['Engineering', 'Business Administration', 'Public Health', 'Fine Arts', 'Education', 'Architecture']:
                pattern = rf'Master of {master_type}(?:\s+in\s+([A-Z][A-Za-z\s,&-]{{5,40}}))?(?:\s+(?:Advance|Designed|Purdue|This|Read)|\.|$)'
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    field = match.group(1) if match.group(1) else ""
                    if field:
                        field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                        degree_name = f"Master of {master_type} in {field}"
                    else:
                        degree_name = f"Master of {master_type}"
                    
                    if degree_name not in seen:
                        degrees.append((degree_name, "MBA" if "Business" in master_type else "Master's"))
                        seen.add(degree_name)
            
            # PhD patterns
            for match in re.finditer(
                r'(?:PhD|Ph\.D\.|Doctor of Philosophy) in ([A-Z][A-Za-z\s,&-]{8,50})(?:\s+(?:Advance|Designed|Purdue|This|Read)|\.|$)',
                text,
                re.IGNORECASE
            ):
                field = match.group(1).strip()
                field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                if field and len(field) > 5 and field not in seen:
                    degree_name = f"Doctor of Philosophy in {field}"
                    degrees.append((degree_name, "PhD"))
                    seen.add(field)
            
            # Abbreviated patterns (MS in X, MA in X, etc.) - with better boundaries
            for match in re.finditer(
                r'\b(?:MS|M\.S\.) in ([A-Z][A-Za-z\s,&-]{8,50})(?:\s+(?:Advance|Designed|Purdue|This|Read|Harness|Build)|\.|,|$)',
                text,
                re.IGNORECASE
            ):
                field = match.group(1).strip()
                field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                if field and len(field) > 5 and field not in seen:
                    degree_name = f"Master of Science in {field}"
                    degrees.append((degree_name, "Master's"))
                    seen.add(field)
            
            for match in re.finditer(
                r'\b(?:MA|M\.A\.) in ([A-Z][A-Za-z\s,&-]{8,50})(?:\s+(?:Advance|Designed|Purdue|This|Read)|\.|,|$)',
                text,
                re.IGNORECASE
            ):
                field = match.group(1).strip()
                field = re.sub(r'\s+(?:Advance|Designed|Purdue|This|Read|more).*$', '', field, flags=re.I).strip()
                if field and len(field) > 5 and field not in seen:
                    degree_name = f"Master of Arts in {field}"
                    degrees.append((degree_name, "Master's"))
                    seen.add(field)
            
            logger.info(f"[catalog_mine] Extracted {len(degrees)} degrees from {url[:60]}...")
            return degrees
    
    except Exception as e:
        logger.error(f"[catalog_mine] Error fetching {url[:60]}: {e}")
        return []


def calculate_confidence(
    extracted_via_regex: bool,
    url: str,
    title: str
) -> float:
    """
    Calculate confidence score for a degree extraction.
    
    Returns score between 0.0 and 1.0.
    """
    score = 0.0
    
    # Base score for extraction method
    if extracted_via_regex:
        score += 0.70
    
    # URL structure signals
    url_lower = url.lower()
    url_signals = ['/program', '/degree', '/academics', '/graduate', '/masters', '/phd', '/mba']
    if any(signal in url_lower for signal in url_signals):
        score += 0.20
    
    # Title content signals
    title_lower = title.lower()
    title_signals = ['degree', 'program', 'master', 'doctor', 'phd', 'mba']
    if any(signal in title_lower for signal in title_signals):
        score += 0.10
    
    # Cap at 1.0 and round
    return round(min(score, 1.0), 2)


async def _extract_degrees_from_pages(
    pages: List[Dict],
    university_name: str = "",
) -> List[Dict]:
    """
    Extract degrees from search result pages using regex + Gemini fallback.
    
    Returns list of degrees with normalized names and confidence scores.
    """
    degrees = []
    regex_extracted = 0
    
    # Try regex extraction first
    for page in pages:
        degree_name, degree_level = extract_degree_from_title_regex(page["title"])
        if degree_name:
            # Calculate confidence using extracted_via_regex=True
            confidence = calculate_confidence(
                extracted_via_regex=True,
                url=page["url"],
                title=page["title"]
            )
            
            # Normalize the degree name
            normalized_name = normalize_degree_name(degree_name)
            
            degrees.append({
                "degree_name": normalized_name,
                "original_name": degree_name,
                "level": degree_level,
                "confidence": confidence,
                "source_url": page["url"],
                "source": "regex",  # Track extraction method
            })
            regex_extracted += 1
    
    logger.info(f"[extract] Regex extraction: {regex_extracted}/{len(pages)} degrees")
    
    # If regex didn't get enough, try Gemini for remaining
    if regex_extracted < len(pages) * 0.7:  # Less than 70% extracted
        logger.info("[extract] Trying Gemini for remaining candidates...")
        gemini_degrees = await extract_degree_names(pages)
        if gemini_degrees:
            # Process Gemini results with normalization and confidence
            for gd in gemini_degrees:
                # Skip if URL already extracted via regex (avoid duplicates)
                if any(d["source_url"] == gd["url"] for d in degrees):
                    continue
                
                degree_name = gd.get("program_name", "")
                if not degree_name.strip():
                    continue
                
                # Find original page for confidence calculation
                original_page = next((p for p in pages if p["url"] == gd["url"]), None)
                if not original_page:
                    continue
                
                confidence = calculate_confidence(
                    extracted_via_regex=False,
                    url=gd["url"],
                    title=original_page["title"]
                )
                
                normalized_name = normalize_degree_name(degree_name)
                
                degrees.append({
                    "degree_name": normalized_name,
                    "original_name": degree_name,
                    "level": gd.get("degree_level", "Unspecified"),
                    "confidence": confidence,
                    "source_url": gd["url"],
                    "source": "gemini",  # Track extraction method
                })
    
    # If still no degrees, fallback to title-based extraction
    if not degrees:
        logger.info("[extract] Falling back to title-based extraction")
        for page in pages:
            # Clean title and use as program name
            title = page["title"]
            # Remove university name
            if university_name:
                title = title.replace(university_name, "").replace(f"- {university_name}", "")
            title = title.strip(" -|")
            
            # Infer degree level from title
            title_lower = title.lower()
            if any(kw in title_lower for kw in ['phd', 'ph.d', 'doctor of philosophy', 'doctoral']):
                level = "PhD"
            elif 'mba' in title_lower:
                level = "MBA"
            elif any(kw in title_lower for kw in ['master', 'msc', 'ms', 'ma', 'meng']):
                level = "Master's"
            elif 'certificate' in title_lower:
                level = "Certificate"
            else:
                level = "Unspecified"
            
            confidence = calculate_confidence(
                extracted_via_regex=False,
                url=page["url"],
                title=page["title"]
            )
            
            normalized_name = normalize_degree_name(title)
            
            degrees.append({
                "degree_name": normalized_name,
                "original_name": title,
                "level": level,
                "confidence": confidence,
                "source_url": page["url"],
                "source": "title",  # Track extraction method
            })
    
    return degrees


def score_catalog_url(url: str) -> int:
    """
    Priority scoring for catalog pages.
    Higher score = more likely to contain comprehensive degree listings.
    """
    url_lower = url.lower()
    score = 0
    
    # High priority catalog patterns
    if "/programs-of-study" in url_lower:
        score += 10
    if "/graduate-catalog" in url_lower:
        score += 10
    if "/graduate-programs" in url_lower:
        score += 8
    if "/degrees" in url_lower and "/offered" in url_lower:
        score += 8
    if "/catalog" in url_lower:
        score += 5
    if "/academics" in url_lower:
        score += 3
    
    # Reject non-catalog pages
    if any(pattern in url_lower for pattern in ["/admissions/", "/tuition/", "/faculty/", "/student/", "/apply/"]):
        score = -100
    
    return score


async def _mine_catalog_pages(catalog_pages: List[Dict], max_pages: int = 5) -> List[Dict]:
    """
    Mine catalog pages for additional degrees.
    
    Increased from 2 to 5 pages with priority scoring.
    Stops early if 50+ degrees found.
    
    Returns list of degrees extracted from catalog HTML.
    """
    degrees = []
    
    # Sort catalog pages by priority score
    scored_pages = [(score_catalog_url(p["url"]), p) for p in catalog_pages]
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    
    # Filter out negative scores (rejected pages)
    valid_pages = [p for score, p in scored_pages if score > 0]
    
    logger.info(f"[catalog_mine] Found {len(valid_pages)} valid catalog pages, mining top {max_pages}...")
    
    for i, catalog_page in enumerate(valid_pages[:max_pages]):
        catalog_degrees = await mine_catalog_page(catalog_page["url"])
        
        for degree_name, degree_level in catalog_degrees:
            # Skip if too short or looks invalid
            if len(degree_name) < 10:
                continue
            
            # Normalize and add
            normalized_name = normalize_degree_name(degree_name)
            
            # HIGHER confidence for catalog degrees (they're authoritative)
            url_lower = catalog_page["url"].lower()
            if any(kw in url_lower for kw in ['/programs-of-study', '/graduate-catalog', '/graduate-programs']):
                confidence = 0.95  # High confidence for official catalogs
            else:
                confidence = 0.85
            
            degrees.append({
                "degree_name": normalized_name,
                "original_name": degree_name,
                "level": degree_level,
                "confidence": confidence,
                "source_url": catalog_page["url"],
                "source": "catalog",  # Track that this came from catalog mining
            })
        
        # Early exit if we have enough degrees
        if len(degrees) >= 50:
            logger.info(f"[catalog_mine] Early exit: {len(degrees)} degrees from {i+1} catalog pages")
            break
    
    logger.info(f"[catalog_mine] Mined {len(degrees)} degrees from catalogs")
    return degrees


def _deduplicate_degrees(degrees: List[Dict]) -> List[Dict]:
    """
    Deduplicate degrees by normalized name, keeping highest confidence version.
    Also validates degree name length.
    
    Returns deduplicated list sorted by confidence.
    """
    unique_by_name = {}
    for d in degrees:
        normalized = d["degree_name"]
        
        # Skip if empty
        if not normalized.strip():
            continue
        
        # Validate length (reject suspiciously long names)
        if not is_valid_degree_length(normalized):
            logger.debug(f"[dedup] Rejected invalid length: {normalized[:80]}")
            continue
        
        # Use canonical key for deduplication
        dedup_key = get_dedup_key(normalized)
        
        # Keep the one with highest confidence
        if dedup_key not in unique_by_name:
            unique_by_name[dedup_key] = d
        else:
            # Compare confidence scores
            if d["confidence"] > unique_by_name[dedup_key]["confidence"]:
                unique_by_name[dedup_key] = d
    
    # Convert back to list
    final_degrees = list(unique_by_name.values())
    
    # Sort by confidence (highest first)
    final_degrees.sort(key=lambda x: x["confidence"], reverse=True)
    
    return final_degrees


async def discover_degrees_simple(
    domain: str,
    university_name: str = "",
    max_results: int = 100,
    use_cache: bool = True,
) -> List[Dict]:
    """
    PRODUCTION-READY DEGREE DISCOVERY - Catalog-First with Caching
    
    OPTIMIZED FLOW (3-15 queries average):
    - Cache: Check cache first (0 queries if cached)
    - Phase 0: 3 catalog queries → mine catalogs → EARLY EXIT if >= 40
    - Phase 1: 5 broad searches → EARLY EXIT if >= 40
    - Phase 2: 10 top fields (only if < 30 degrees)
    - Phase 3: 10 more fields (only if < 40 degrees)
    
    KEY FEATURES:
    1. Caching: Returns cached results immediately (saves thousands of API calls)
    2. Catalog-first: Single catalog page = 50-200 degrees
    3. Early exit: Stop when threshold met
    4. Smart filtering: Reject career/outcomes/admissions URLs
    5. Title cleanup: Remove junk suffixes, trim at stop words
    6. Length validation: Reject suspiciously long degree names
    7. Aggressive deduplication: Canonical normalization (MS = Master of Science)
    
    Expected API usage:
    - Best case: 0 queries (cached)
    - Average: 3-8 queries
    - Worst case: 15-18 queries (was 128!)
    """
    logger.info(f"[production_search] Starting degree search for {domain}")
    
    # ── CACHE LOOKUP ──────────────────────────────────────────────────
    if use_cache:
        cached = load_from_cache(domain)
        if cached is not None:
            logger.info(f"[production_search] ✓ Returning {len(cached)} degrees from cache")
            return cached
    
    all_degrees = []
    total_queries = 0
    
    # ── PHASE 0: CATALOG-FIRST (3 queries) ────────────────────────────
    logger.info(f"[production_search] Phase 0: Searching for catalog pages...")
    catalog_queries = build_catalog_queries(domain)
    total_queries += len(catalog_queries)
    
    # Budget protection
    if total_queries >= MAX_QUERIES_PER_UNIVERSITY:
        logger.warning(f"[production_search] Query budget exhausted ({total_queries}/{MAX_QUERIES_PER_UNIVERSITY})")
        return _format_output(_deduplicate_degrees(all_degrees))
    
    catalog_results = await search_degrees_serpapi(domain, catalog_queries)
    
    if catalog_results:
        logger.info(f"[production_search] Phase 0: Got {len(catalog_results)} catalog results")
        
        # Filter for actual catalog pages
        catalog_pages = []
        for r in catalog_results:
            url_lower = r["url"].lower()
            if any(kw in url_lower for kw in ['catalog', 'bulletin', 'programs', 'degrees']):
                catalog_pages.append(r)
        
        if catalog_pages:
            logger.info(f"[production_search] Phase 0: Mining {min(len(catalog_pages), 10)} catalog pages...")
            catalog_degrees = await _mine_catalog_pages(catalog_pages[:10])  # Mine up to 10 pages
            all_degrees.extend(catalog_degrees)
            
            # Deduplicate
            unique_degrees = _deduplicate_degrees(all_degrees)
            logger.info(f"[production_search] Phase 0: {len(unique_degrees)} unique degrees from catalogs")
            
            # EARLY EXIT if we hit target
            if len(unique_degrees) >= 40:
                logger.info(f"[production_search] ✓ EARLY EXIT: {len(unique_degrees)} degrees from {total_queries} queries")
                result = _format_output(unique_degrees)
                if use_cache:
                    save_to_cache(domain, result)
                return result
    
    # ── PHASE 1: BROAD SEARCHES (5 queries) ───────────────────────────
    logger.info(f"[production_search] Phase 1: Running 5 broad searches...")
    phase1_queries = build_search_queries(domain)
    total_queries += len(phase1_queries)
    
    # Budget protection
    if total_queries >= MAX_QUERIES_PER_UNIVERSITY:
        logger.warning(f"[production_search] Query budget exhausted ({total_queries}/{MAX_QUERIES_PER_UNIVERSITY})")
        result = _format_output(_deduplicate_degrees(all_degrees))
        if use_cache:
            save_to_cache(domain, result)
        return result
    
    phase1_results = await search_degrees_serpapi(domain, phase1_queries)
    if not phase1_results:
        logger.warning(f"[production_search] No Phase 1 results, returning catalog degrees")
        result = _format_output(_deduplicate_degrees(all_degrees))
        if use_cache:
            save_to_cache(domain, result)
        return result
    
    logger.info(f"[production_search] Phase 1: Got {len(phase1_results)} search results")
    
    # Filter and extract
    degree_pages = filter_degree_pages(phase1_results)
    if degree_pages:
        top_pages = degree_pages[:max_results]
        degrees = await _extract_degrees_from_pages(top_pages, university_name)
        all_degrees.extend(degrees)
    
    # Deduplicate
    unique_degrees = _deduplicate_degrees(all_degrees)
    logger.info(f"[production_search] Phase 1: {len(unique_degrees)} unique degrees")
    
    # EARLY EXIT if we hit target
    if len(unique_degrees) >= 40:
        logger.info(f"[production_search] ✓ EARLY EXIT: {len(unique_degrees)} degrees from {total_queries} queries")
        result = _format_output(unique_degrees)
        if use_cache:
            save_to_cache(domain, result)
        return result
    
    # ── PHASE 2: TOP FIELDS (only if < 30) ────────────────────────────
    if len(unique_degrees) < 30:
        # Budget check before Phase 2
        if total_queries >= MAX_QUERIES_PER_UNIVERSITY:
            logger.warning(f"[production_search] Query budget exhausted ({total_queries}/{MAX_QUERIES_PER_UNIVERSITY})")
            result = _format_output(unique_degrees)
            if use_cache:
                save_to_cache(domain, result)
            return result
        
        logger.info(f"[production_search] Phase 2: Only {len(unique_degrees)} degrees, running 10 field queries...")
        phase2_queries = build_field_queries_phase2(domain)
        
        # Enforce budget by limiting queries
        queries_remaining = MAX_QUERIES_PER_UNIVERSITY - total_queries
        if queries_remaining < len(phase2_queries):
            logger.warning(f"[production_search] Budget limit: reducing Phase 2 to {queries_remaining} queries")
            phase2_queries = phase2_queries[:queries_remaining]
        
        total_queries += len(phase2_queries)
        
        phase2_results = await search_degrees_serpapi(domain, phase2_queries)
        if phase2_results:
            # Check if we got meaningful new results
            if len(phase2_results) < 20:
                logger.info(f"[production_search] Phase 2: Only {len(phase2_results)} results, university likely has few programs")
            
            phase2_pages = filter_degree_pages(phase2_results)
            if phase2_pages:
                phase2_degrees = await _extract_degrees_from_pages(phase2_pages[:max_results], university_name)
                all_degrees.extend(phase2_degrees)
                
                unique_degrees = _deduplicate_degrees(all_degrees)
                logger.info(f"[production_search] Phase 2: {len(unique_degrees)} unique degrees")
                
                # EARLY EXIT
                if len(unique_degrees) >= 40:
                    logger.info(f"[production_search] ✓ EARLY EXIT: {len(unique_degrees)} degrees from {total_queries} queries")
                    result = _format_output(unique_degrees)
                    if use_cache:
                        save_to_cache(domain, result)
                    return result
    else:
        logger.info(f"[production_search] Phase 2: SKIPPED (already have {len(unique_degrees)} degrees)")
    
    # ── PHASE 3: MORE FIELDS (only if < 40) ───────────────────────────
    if len(unique_degrees) < 40:
        # Budget check before Phase 3
        if total_queries >= MAX_QUERIES_PER_UNIVERSITY:
            logger.warning(f"[production_search] Query budget exhausted ({total_queries}/{MAX_QUERIES_PER_UNIVERSITY})")
            result = _format_output(unique_degrees)
            if use_cache:
                save_to_cache(domain, result)
            return result
        
        logger.info(f"[production_search] Phase 3: Only {len(unique_degrees)} degrees, running 10 more field queries...")
        phase3_queries = build_field_queries_phase3(domain)
        
        # Enforce budget by limiting queries
        queries_remaining = MAX_QUERIES_PER_UNIVERSITY - total_queries
        if queries_remaining < len(phase3_queries):
            logger.warning(f"[production_search] Budget limit: reducing Phase 3 to {queries_remaining} queries")
            phase3_queries = phase3_queries[:queries_remaining]
        
        total_queries += len(phase3_queries)
        
        phase3_results = await search_degrees_serpapi(domain, phase3_queries)
        if phase3_results:
            phase3_pages = filter_degree_pages(phase3_results)
            if phase3_pages:
                phase3_degrees = await _extract_degrees_from_pages(phase3_pages[:max_results], university_name)
                all_degrees.extend(phase3_degrees)
                
                unique_degrees = _deduplicate_degrees(all_degrees)
                logger.info(f"[production_search] Phase 3: {len(unique_degrees)} unique degrees")
    else:
        logger.info(f"[production_search] Phase 3: SKIPPED (already have {len(unique_degrees)} degrees)")
    
    # ── FINAL OUTPUT ───────────────────────────────────────────────────
    logger.info(
        f"[production_search] ✓ COMPLETE: {len(unique_degrees)} degrees from {total_queries} queries "
        f"(target: 3-15)"
    )
    
    result = _format_output(unique_degrees)
    if use_cache:
        save_to_cache(domain, result)
    return result


def _format_output(degrees: List[Dict]) -> List[Dict]:
    """Format final output with source tracking."""
    output = []
    for d in degrees:
        output.append({
            "degree_name": d["degree_name"],
            "level": d["level"],
            "confidence": d["confidence"],
            "source_url": d["source_url"],
            "source": d.get("source", "search"),  # Track extraction source
        })
    return output
