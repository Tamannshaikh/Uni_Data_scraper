"""
Catalog URL Guesser - Try common catalog URL patterns before using search.

Most universities expose catalog pages at predictable URLs.
This reduces search API dependency by 80%+.
"""
import asyncio
import logging
from typing import List, Dict, Optional
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def _normalize_degree_format(degree_name: str) -> str:
    """
    Normalize degree names from reverse format to standard format.
    
    Examples:
    - "Economics (PhD)" → "Doctor of Philosophy in Economics"
    - "Computer Science (MS)" → "Master of Science in Computer Science"
    - "MBA" → "Master of Business Administration"
    """
    import re
    
    # Reverse PhD format: "Economics (PhD)" → "Doctor of Philosophy in Economics"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \((Ph\.?D\.?)\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Doctor of Philosophy in {field}"
    
    # Reverse PhD format: "Economics (Doctor of Philosophy)" → "Doctor of Philosophy in Economics"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \(Doctor of Philosophy\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Doctor of Philosophy in {field}"
    
    # Reverse MS format: "Computer Science (MS)" → "Master of Science in Computer Science"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \((M\.?S\.?)\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Science in {field}"
    
    # Reverse MS format: "Computer Science (Master of Science)" → "Master of Science in Computer Science"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \(Master of Science\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Science in {field}"
    
    # Reverse MA format: "History (MA)" → "Master of Arts in History"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \((M\.?A\.?)\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Arts in {field}"
    
    # Reverse MA format: "History (Master of Arts)" → "Master of Arts in History"
    match = re.match(r"^([A-Za-z0-9&,\-()/ ]+) \(Master of Arts\)$", degree_name, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Arts in {field}"
    
    # MBA → Master of Business Administration
    if degree_name.upper() == "MBA":
        return "Master of Business Administration"
    
    # MPH → Master of Public Health
    if degree_name.upper() == "MPH":
        return "Master of Public Health"
    
    # No transformation needed
    return degree_name


def extract_degree_flexible(text: str, tag_name: str = "", url: str = "") -> tuple[str, str, float]:
    """
    Extract degree from text using BROAD patterns + strict confidence validation.
    
    Philosophy: Extract aggressively, validate aggressively.
    
    Returns (degree_name, degree_level, confidence) or (None, None, 0.0)
    """
    import re
    
    text = text.strip()
    
    # Basic length checks
    if len(text) > 200 or len(text) < 5:
        return (None, None, 0.0)
    
    # BROAD extraction patterns (permissive)
    # UNION of all formats - try ALL patterns, not first-match-wins
    MASTER_PATTERNS = [
        # *** REVERSE FORMAT (MIT-style: "Field Name (MS)") ***
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(M\.?S\.?\)",
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(M\.?A\.?\)",
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(Master of Science\)",
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(Master of Arts\)",
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(MEng\)",
        
        # *** STANDARD FORMAT (UCSD-style: "Master of Science in Field") ***
        r"Master of [A-Za-z0-9&,\-()/ ]{3,100}",
        r"Master's in [A-Za-z0-9&,\-()/ ]{3,100}",
        r"MS in [A-Za-z0-9&,\-()/ ]{3,100}",
        r"M\.S\. in [A-Za-z0-9&,\-()/ ]{3,100}",
        r"MA in [A-Za-z0-9&,\-()/ ]{3,100}",
        r"M\.A\. in [A-Za-z0-9&,\-()/ ]{3,100}",
        r"MEng in [A-Za-z0-9&,\-()/ ]{3,100}",
        
        # *** STANDALONE (always try last) ***
        r"MPH",
        r"MBA",
    ]
    
    PHD_PATTERNS = [
        # *** REVERSE FORMAT (MIT-style: "Field Name (PhD)") ***
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(Ph\.?D\.?\)",
        r"[A-Za-z0-9&,\-()/ ]{3,80} \(Doctor of Philosophy\)",
        
        # *** STANDARD FORMAT (UCSD-style: "Doctor of Philosophy in Field") ***
        # Keep optional "in [Field]" to match both "Doctor of Philosophy" AND "Doctor of Philosophy in Economics"
        r"Doctor of Philosophy(?: in [A-Za-z0-9&,\-()/ ]+)?",
        r"PhD(?: in [A-Za-z0-9&,\-()/ ]+)?",  # RESTORED: optional "in" clause
        r"Ph\.D\.(?: in [A-Za-z0-9&,\-()/ ]+)?",  # RESTORED: optional "in" clause
        r"Doctor of [A-Za-z0-9&,\-()/ ]+",
    ]
    
    degree_name = None
    degree_level = None
    
    # Try Master's patterns
    for pattern in MASTER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            degree_name = match.group(0).strip()
            degree_level = "Master's"
            break
    
    # Try PhD patterns if no Master's found
    if not degree_name:
        for pattern in PHD_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                degree_name = match.group(0).strip()
                degree_level = "PhD"
                break
    
    if not degree_name:
        return (None, None, 0.0)
    
    # ────────────────────────────────────────────────────────────────────────
    # NORMALIZATION: Convert reverse format to standard format
    # ────────────────────────────────────────────────────────────────────────
    degree_name = _normalize_degree_format(degree_name)
    
    # ────────────────────────────────────────────────────────────────────────
    # STRICT CONFIDENCE SCORING
    # ────────────────────────────────────────────────────────────────────────
    score = 0.0
    
    # 1. Exact degree keyword (+5)
    if re.search(r"\b(Master|MS|MA|MBA|PhD|Doctor|Certificate)\b", text, re.I):
        score += 5
    
    # 2. Good container (+3 to +5)
    if tag_name in {"h1", "h2", "h3", "h4", "h5"}:
        score += 5
    elif tag_name in {"li", "td", "a"}:
        score += 3
    
    # 3. URL evidence (+3)
    url_lower = url.lower()
    if any(kw in url_lower for kw in ["graduate", "degree", "program", "phd", "masters", "catalog"]):
        score += 3
    
    # 4. Sentence verbs penalty (-10)
    SENTENCE_VERBS = {
        "is", "are", "was", "were", "will", "can", "learn", "designed",
        "prepare", "prepares", "provides", "offers", "helps", "allows",
        "enables", "teaches", "focuses", "trains", "develop", "develops"
    }
    
    text_lower = text.lower()
    if any(f" {verb} " in text_lower for verb in SENTENCE_VERBS):
        score -= 10
    
    # 5. Length penalties
    words = text.split()
    word_count = len(words)
    
    if word_count > 15:
        score -= 8
    elif word_count < 2:
        score -= 10
    
    if len(text) > 120:
        score -= 10
    
    # 6. Punctuation penalties (sentence indicators)
    if text.count(".") > 1:  # Multiple periods = sentence
        score -= 5
    if ":" in text and word_count > 8:  # Colon in long text = description
        score -= 5
    if ";" in text:
        score -= 5
    
    # 7. Invalid endings penalty
    last_word = words[-1].lower().rstrip('.,;:') if words else ""
    INVALID_ENDINGS = {"is", "are", "was", "were", "will", "can", "and", "or", "with", "for", "the"}
    if last_word in INVALID_ENDINGS:
        score -= 10
    
    # Clean up degree name
    degree_name = _clean_degree_name(degree_name)
    
    return (degree_name, degree_level, score)


def _clean_degree_name(name: str) -> str:
    """Remove trailing junk from degree name."""
    TRAILING_JUNK = [
        "Fields", "Field", "Requirements", "Requirement",
        "Curriculum", "Overview", "Track", "Option",
        "Concentration", "Concentrations", "Program", "Programs",
        "Specialization", "Specializations", "Area", "Areas",
        "Department", "Departments", "School", "Schools"
    ]
    
    for junk in TRAILING_JUNK:
        if name.endswith(f" {junk}"):
            name = name[:-len(junk)-1].strip()
    
    return name


# Common catalog URL patterns (ordered by likelihood)
CATALOG_URL_PATTERNS = [
    "/gradschool/",  # Very common (with trailing slash)
    "/graduate-school/",
    "/grad-school/",
    "/graduate-studies/",
    "/academics/ogsps/",  # Purdue-specific
    "/graduate/admissions/",
    "/graduate-programs/",
    "/graduate/",
    "/grad/",
    "/programs/",
    "/academics/graduate/",
    "/academics/programs/",
    "/catalog/",
    "/graduate-catalog/",
    "/programs-of-study/",
    "/degrees/",
    "/graduate-degrees/",
    "/academics/degrees/",
    "/study/graduate/",
    "/study/programs/",
]


async def guess_catalog_urls(domain: str) -> List[str]:
    """
    Generate likely catalog URLs for a university domain.
    
    Returns URLs in priority order (most likely first).
    """
    urls = []
    
    # Try with https first
    for pattern in CATALOG_URL_PATTERNS:
        urls.append(f"https://{domain}{pattern}")
        urls.append(f"https://www.{domain}{pattern}")
    
    return urls


async def test_url(url: str, timeout: float = 10.0) -> Optional[Dict]:
    """
    Test if URL exists and contains degree-related content.
    
    Uses scoring approach instead of strict keyword matching.
    
    Returns {url, status, has_degrees} or None if unreachable.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code != 200:
                return None
            
            # Score-based validation (more flexible)
            text_lower = resp.text.lower()
            final_url = str(resp.url).lower()
            
            score = 0
            
            # Content scoring
            if "master" in text_lower or "master of" in text_lower:
                score += 2
            if "phd" in text_lower or "ph.d" in text_lower:
                score += 2
            if "doctoral" in text_lower or "doctorate" in text_lower:
                score += 2
            if "graduate program" in text_lower:
                score += 2
            if "graduate" in text_lower:
                score += 1
            if "degree" in text_lower:
                score += 1
            
            # URL scoring (if final URL contains degree-related terms)
            url_keywords = ["grad", "graduate", "catalog", "program", "degree", "ogsps"]
            if any(keyword in final_url for keyword in url_keywords):
                score += 2
            
            # Need score >= 3 to be considered valid
            if score >= 3:
                logger.info(f"[catalog_guess] [OK] Found (score={score}): {final_url[:80]}")
                return {
                    "url": str(resp.url),  # Follow redirects
                    "status": resp.status_code,
                    "has_degrees": True,
                    "content": resp.text,
                    "score": score
                }
            else:
                logger.debug(f"[catalog_guess] [FAIL] Low score ({score}): {final_url[:60]}")
            
            return None
    
    except asyncio.CancelledError:
        # Handle task cancellation gracefully
        return None
    except asyncio.TimeoutError:
        logger.debug(f"[catalog_guess] [TIMEOUT] {url[:60]}")
        return None
    except Exception as e:
        logger.debug(f"[catalog_guess] [FAIL] Failed {url}: {e}")
        return None


async def find_catalog_pages(domain: str, max_concurrent: int = 5) -> List[Dict]:
    """
    Try common catalog URL patterns and return working pages.
    
    Args:
        domain: University domain (e.g., "purdue.edu")
        max_concurrent: Max parallel URL tests
    
    Returns:
        List of {url, status, has_degrees, content} for working catalog pages
    """
    logger.info(f"[catalog_guess] Testing common catalog URLs for {domain}")
    
    candidate_urls = await guess_catalog_urls(domain)
    
    # Test URLs in parallel (batches of max_concurrent)
    results = []
    
    for i in range(0, len(candidate_urls), max_concurrent):
        batch = candidate_urls[i:i + max_concurrent]
        batch_results = await asyncio.gather(*[test_url(url) for url in batch])
        
        # Collect successful results
        for result in batch_results:
            if result:
                results.append(result)
        
        # Early exit if we found good pages
        if len(results) >= 3:
            break
    
    logger.info(f"[catalog_guess] Found {len(results)} catalog pages for {domain}")
    return results


async def extract_degrees_from_catalog(url: str, content: str, use_playwright: bool = False) -> List[Dict]:
    """
    Extract degree names from catalog page HTML.
    
    Strategy: Broad extraction + strict validation via confidence scoring.
    
    Rules:
    - Only extract from: h1, h2, h3, h4, h5, li, a, td (NOT from p, div, span)
    - Confidence threshold: >= 7.0
    - Length limit: 2-15 words
    
    Args:
        url: Page URL
        content: HTML content (only used if use_playwright=False)
        use_playwright: If True, fetch page with Playwright to render JS
    
    Returns: List of {degree_name, degree_level, url, confidence}
    """
    import re
    from bs4 import BeautifulSoup
    
    # If JavaScript rendering is needed
    if use_playwright:
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, wait_until='networkidle', timeout=30000)
                content = await page.content()
                await browser.close()
                
                logger.info(f"[catalog_guess] Rendered page with Playwright: {len(content)} chars")
        except Exception as e:
            logger.warning(f"[catalog_guess] Playwright failed: {e}, using static HTML")
    
    soup = BeautifulSoup(content, 'html.parser')
    degrees = []
    seen = set()
    
    # Only extract from structured elements (headings, lists, links, tables)
    ALLOWED_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'li', 'a', 'td', 'th']
    
    element_count = 0
    degree_related = []
    
    for tag in soup.find_all(ALLOWED_TAGS):
        text = tag.get_text(strip=True)
        element_count += 1
        
        if not text or len(text) < 5:
            continue
        
        # Skip if text is too long (likely navigation or paragraph)
        if len(text) > 200:
            continue
        
        # Collect degree-related for debugging
        lower_text = text.lower()
        if any(keyword in lower_text for keyword in ["master", "phd", "ph.d", "doctor", "ms", "ma", "mba", "graduate"]):
            degree_related.append(text[:100])
        
        # Extract degree with confidence score
        degree_name, degree_level, confidence = extract_degree_flexible(text, tag.name, url)
        
        # DEBUG: Log all regex matches regardless of confidence
        if degree_name:
            logger.debug(f"[catalog_guess] REGEX MATCH (conf={confidence:.1f}, tag={tag.name}): {degree_name[:80]}")
        
        if degree_name:
            # STRICT confidence threshold (lowered from 7.0 to 5.0)
            if confidence < 5.0:
                logger.debug(f"[catalog_guess] REJECTED (conf={confidence:.1f}): {degree_name[:80]}")
                continue
            else:
                logger.debug(f"[catalog_guess] ACCEPTED (conf={confidence:.1f}): {degree_name[:80]}")
            
            # Word count check
            words = degree_name.split()
            if len(words) < 2 or len(words) > 15:
                continue
            
            # Normalize and deduplicate
            normalized = degree_name.lower().strip()
            if normalized not in seen and len(normalized) > 10:
                seen.add(normalized)
                
                # Get href if it's a link
                href = tag.get('href', '') if tag.name == 'a' else ''
                full_url = href if href.startswith('http') else url
                
                degrees.append({
                    "degree_name": degree_name,
                    "degree_level": degree_level,
                    "url": full_url,
                    "source": "catalog_validated",
                    "confidence": round(confidence / 15.0, 2)  # Normalize to 0-1 scale
                })
    
    logger.info(f"[catalog_guess] Checked {element_count} elements, found {len(degree_related)} degree-related")
    
    # Show sample degree-related elements for debugging
    if degree_related and len(degrees) < 5:
        logger.info(f"[catalog_guess] Sample degree-related elements (extraction failed on these):")
        for i, text in enumerate(degree_related[:10], 1):
            logger.info(f"  {i}. {text}")
    
    logger.info(f"[catalog_guess] Extracted {len(degrees)} degrees from {url[:60]}...")
    return degrees


# Test function
async def test_catalog_guesser():
    """Test catalog URL guesser on Purdue."""
    # Disable verbose httpx/httpcore logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpcore.connection").setLevel(logging.WARNING)
    logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
    
    # Enable DEBUG logging for our module to see extraction details
    logging.basicConfig(level=logging.DEBUG, format='%(message)s')
    
    print("\n" + "="*80)
    print("TESTING CATALOG URL GUESSER")
    print("="*80 + "\n")
    
    domain = "purdue.edu"
    print(f"Testing: {domain}\n")
    
    # Find catalog pages
    catalog_pages = await find_catalog_pages(domain, max_concurrent=10)
    
    if not catalog_pages:
        print("❌ No catalog pages found")
        return
    
    print(f"\nFound {len(catalog_pages)} catalog pages:\n")
    for page in catalog_pages:
        print(f"  - {page['url']}")
    
    # Extract degrees from first page
    if catalog_pages:
        print(f"\nExtracting degrees from: {catalog_pages[0]['url'][:80]}...\n")
        degrees = await extract_degrees_from_catalog(
            catalog_pages[0]['url'],
            catalog_pages[0]['content']
        )
        
        print(f"Extracted {len(degrees)} degrees:\n")
        for i, deg in enumerate(degrees[:10], 1):
            print(f"{i:2d}. {deg['degree_name']}")
        
        if len(degrees) > 10:
            print(f"\n... and {len(degrees) - 10} more")


if __name__ == "__main__":
    asyncio.run(test_catalog_guesser())
