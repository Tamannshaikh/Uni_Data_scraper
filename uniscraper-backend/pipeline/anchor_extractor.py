"""
ANCHOR-ONLY EXTRACTOR

The simplest possible approach:
1. Extract ALL <a> tags
2. Keep only those with degree keywords in text OR URL
3. Filter out junk
4. Return {degree_name, url}

No scoring. No confidence. No PageType. No text extraction.
"""
import logging
from typing import List, Dict
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


# Degree type indicators - must be present for text matching
DEGREE_TYPES = [
    "master of", "master's", "master in",
    "m.s.", "m.a.", "m.sc.", "m.eng.", "m.arch.", "m.f.a.", "m.p.h.", "m.phil.", "m.res.", "m.b.a.",
    "ms in", "ma in", "mba", "msc in",
    "phd", "ph.d", "ph.d.", "doctor of", "doctoral program",
    "certificate in", "graduate certificate",
    "j.d.", "ll.m.", "ed.d.", "d.n.p."
]

# URL patterns that indicate a program page
DEGREE_URL_PATTERNS = [
    "/program/", "/degree/", "/masters/", "/master/",
    "/phd/", "/doctoral/", "/doctorate/",
    "/graduate/", "/postgraduate/",
    "/course/", "/curriculum/"
]

# Junk text to filter out - EXPANDED
JUNK_TEXT = [
    # Navigation & meta
    "admissions", "apply", "apply now", "how to apply", "application",
    "overview", "general information", "about", "why study", "why choose",
    "contact", "contact us", "email", "phone",
    "home", "search", "menu", "toggle", "close", "open",
    
    # Financial & admin
    "tuition", "fees", "costs", "funding", "financial aid", "scholarships",
    
    # Generic headers
    "graduate programs", "master's programs", "doctoral programs",
    "academic programs", "online programs", "degree programs",
    "programs of study", "areas of study", "fields of study",
    "taught master's", "research degrees",
    
    # Student services
    "student support", "student life", "campus", "campus map",
    "resources", "facilities", "library",
    
    # Generic actions
    "learn more", "read more", "view details", "more info", "find out more",
    "download", "view all", "see all", "browse", "explore",
    
    # Events & news
    "news", "events", "blog", "meet us", "open days",
    
    # Faculty & research
    "faculty", "staff", "directory", "research", "research areas",
    
    # Undergraduate
    "undergraduate", "bachelor", "bachelors",
    
    # Specific junk observed
    "graduate education", "graduate study", "degree requirements",
    "general requirements", "courses", "course catalog",
    "graduate catalog", "other institutions", "medical requirements",
    "why manchester", "teaching and learning", "prospective students",
    "international students", "current students",
    "graduate & professional schools", "degrees offered",
    "bicentenary", "studentships", "fellowships"
]


def extract_programs(url: str, html: str) -> List[Dict]:
    """
    Extract programs from anchor tags only.
    
    Args:
        url: Base URL of the page
        html: HTML content
    
    Returns:
        List of {degree_name, url}
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    programs = []
    seen_urls = set()
    
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        if not href or href.startswith('#'):
            continue
        
        # Make absolute URL
        if href.startswith('http'):
            absolute_url = href
        elif href.startswith('/'):
            absolute_url = urljoin(url, href)
        else:
            absolute_url = urljoin(url, href)
        
        # Skip duplicates
        if absolute_url in seen_urls:
            continue
        
        # Get anchor text
        text = link.get_text(strip=True)
        
        # Length check
        if len(text) < 3 or len(text) > 120:
            continue
        
        text_lower = text.lower()
        url_lower = absolute_url.lower()
        
        # Filter junk FIRST (before checking degree patterns)
        if any(junk in text_lower for junk in JUNK_TEXT):
            continue
        
        # Check if text contains a degree type indicator
        has_degree_text = any(dtype in text_lower for dtype in DEGREE_TYPES)
        
        # Check if URL looks like a program page
        has_degree_url = any(pattern in url_lower for pattern in DEGREE_URL_PATTERNS)
        
        # REQUIRE: degree text OR (degree URL AND reasonable length)
        if has_degree_text:
            # Text explicitly mentions a degree type - accept
            pass
        elif has_degree_url and 15 <= len(text) <= 100:
            # URL looks like a program page AND text is reasonable length - accept
            pass
        else:
            # Neither condition met - reject
            continue
        
        # Clean text
        degree_name = text.strip()
        
        # Remove common suffixes
        for suffix in [' ›', ' »', ' >', ' →', ' *']:
            if degree_name.endswith(suffix):
                degree_name = degree_name[:-len(suffix)].strip()
        
        seen_urls.add(absolute_url)
        
        programs.append({
            'degree_name': degree_name,
            'url': absolute_url
        })
    
    logger.info(f"[anchor_extractor] Extracted {len(programs)} programs from {url[:60]}")
    
    return programs


def deduplicate_programs(programs: List[Dict]) -> List[Dict]:
    """Simple deduplication by normalized name."""
    seen = set()
    unique = []
    
    for prog in programs:
        normalized = prog['degree_name'].lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(prog)
    
    return unique
