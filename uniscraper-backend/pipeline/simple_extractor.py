"""
SIMPLE DEGREE EXTRACTOR

No scoring. No validation. No confidence thresholds.
Just extract anything that looks like a degree name.

Philosophy: Be extremely permissive. Let deduplication handle duplicates.
"""
import re
from typing import List, Dict, Set
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


# RULE 1: Degree keywords - text MUST contain these to be considered
DEGREE_KEYWORDS = [
    "master",
    "phd",
    "doctor",
    "bachelor",
    "mba",
    "msc",
    "m.s",
    "m.a",
    "m.eng",
    "mfa",
    "certificate",
    "jd",
    "llm",
    "edd",
    "mph",
    "mres",
    "mphil",
]

# RULE 2: Junk keywords - reject if ANY of these appear
JUNK_KEYWORDS = [
    "admissions",
    "funding",
    "fees",
    "tuition",
    "campus map",
    "contact us",
    "why manchester",
    "student support",
    "apply",
    "overview",
    "prospective",
    "news",
    "events",
    "directory",
    "faculty",
    "resources",
    "about",
    "careers",
    "visit",
    "staff",
    "leadership",
    "mission",
    "history",
    "open up a career",
    "undertake a phd",
    "courses at",
    "copies of official",
    "translations if not",
    "@manchester.ac.uk",
    "http://",
    "https://",
    "uk students",
    "international",
    "per annum",
]

# Category headers - not actual degrees
CATEGORY_HEADERS = [
    "programs",
    "graduate programs",
    "online programs",
    "academic programs",
    "master's programs",
    "masters programs",
    "doctoral programs",
    "phd programs",
    "degree programs",
]


def extract_degrees_simple(url: str, html: str) -> List[Dict]:
    """
    Extract degree names from HTML - THREE SIMPLE RULES.
    
    RULE 1: Must contain degree keywords (master, phd, mba, etc.)
    RULE 2: Reject junk keywords (admissions, fees, overview, etc.)
    RULE 3: Length sanity check (8-120 chars)
    
    Returns: List of {degree_name, url}
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # ═══════════════════════════════════════════════════════════════════
    # IGNORE: Navigation elements completely
    # ═══════════════════════════════════════════════════════════════════
    for tag in soup(['nav', 'header', 'footer', 'aside', 'script', 'style']):
        tag.decompose()
    
    degrees = []
    seen = set()
    
    # ═══════════════════════════════════════════════════════════════════
    # ONLY check semantic content tags
    # ═══════════════════════════════════════════════════════════════════
    tags_to_check = ['h1', 'h2', 'h3', 'h4', 'li', 'a', 'td']
    
    for tag in soup.find_all(tags_to_check):
        text = tag.get_text(strip=True)
        
        # ═══════════════════════════════════════════════════════════════
        # RULE 3: Length sanity check
        # ═══════════════════════════════════════════════════════════════
        if not text or len(text) < 8 or len(text) > 120:
            continue
        
        text_lower = text.lower()
        
        # ═══════════════════════════════════════════════════════════════
        # RULE 1: MUST contain degree keywords
        # ═══════════════════════════════════════════════════════════════
        has_degree_keyword = any(keyword in text_lower for keyword in DEGREE_KEYWORDS)
        
        if not has_degree_keyword:
            # No degree keyword = skip immediately
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # RULE 2: Reject junk keywords
        # ═══════════════════════════════════════════════════════════════
        has_junk = any(junk in text_lower for junk in JUNK_KEYWORDS)
        
        if has_junk:
            # Contains junk keyword = reject
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # Reject category headers (not actual degrees)
        # ═══════════════════════════════════════════════════════════════
        if text_lower in CATEGORY_HEADERS:
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # Clean the degree text
        # ═══════════════════════════════════════════════════════════════
        degree_name = _clean_degree_text(text)
        
        if not degree_name:
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # Final check: cleaned text must STILL contain degree keywords
        # ═══════════════════════════════════════════════════════════════
        degree_name_lower = degree_name.lower()
        still_has_degree_keyword = any(keyword in degree_name_lower for keyword in DEGREE_KEYWORDS)
        
        if not still_has_degree_keyword:
            # Cleaning removed the degree keyword - reject
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # Reject if it's still a category header after cleaning
        # ═══════════════════════════════════════════════════════════════
        if degree_name_lower in CATEGORY_HEADERS:
            continue
        
        # ═══════════════════════════════════════════════════════════════
        # Final length check after cleaning
        # ═══════════════════════════════════════════════════════════════
        if len(degree_name) < 8 or len(degree_name) > 120:
            continue
        
        # Deduplicate
        normalized = degree_name.lower().strip()
        if normalized in seen:
            continue
        
        seen.add(normalized)
        
        # Get the link if it's an <a> tag
        program_url = url
        if tag.name == 'a' and tag.get('href'):
            href = tag.get('href', '')
            if href.startswith('http'):
                program_url = href
            elif href.startswith('/'):
                from urllib.parse import urljoin
                program_url = urljoin(url, href)
        
        degrees.append({
            'degree_name': degree_name,
            'url': program_url,
            'source': 'simple_extractor'
        })
    
    logger.info(f"[simple_extractor] Extracted {len(degrees)} degrees from {url[:60]}")
    
    return degrees


def _clean_degree_text(text: str) -> str:
    """
    Clean up degree text - simple cleaning only.
    """
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Skip empty
    if len(text) < 8:
        return None
    
    text_lower = text.lower()
    
    # ═══════════════════════════════════════════════════════════════════
    # Remove common UI suffixes
    # ═══════════════════════════════════════════════════════════════════
    junk_suffixes = [
        ' Toggle', ' ›', ' »', ' >', ' <', 
        ' More Info', ' Learn More', ' Apply Now',
        ' Read More', ' View Details', ' Details',
        ' (link is external)', ' (opens in new window)',
        '*',  # Like "PhD*"
    ]
    
    for suffix in junk_suffixes:
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
    
    # ═══════════════════════════════════════════════════════════════════
    # Normalize common abbreviations
    # ═══════════════════════════════════════════════════════════════════
    text = _normalize_degree_abbreviations(text)
    
    # Final length check
    if len(text) < 8 or len(text) > 120:
        return None
    
    return text


def _normalize_degree_abbreviations(text: str) -> str:
    """
    Normalize common degree abbreviations.
    
    Examples:
    - "Computer Science (MS)" -> "Master of Science in Computer Science"
    - "Economics (PhD)" -> "Doctor of Philosophy in Economics"  
    - "MBA" -> "Master of Business Administration"
    """
    # Reverse format: "Field (MS)" -> "Master of Science in Field"
    match = re.match(r'^(.+?)\s*\((M\.?S\.?C?\.?)\)$', text, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Science in {field}"
    
    match = re.match(r'^(.+?)\s*\((M\.?A\.?)\)$', text, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Arts in {field}"
    
    match = re.match(r'^(.+?)\s*\((Ph\.?D\.?|DPhil)\)$', text, re.I)
    if match:
        field = match.group(1).strip()
        return f"Doctor of Philosophy in {field}"
    
    match = re.match(r'^(.+?)\s*\((M\.?Eng\.?)\)$', text, re.I)
    if match:
        field = match.group(1).strip()
        return f"Master of Engineering in {field}"
    
    # Standalone abbreviations
    if text.upper() == 'MBA':
        return "Master of Business Administration"
    if text.upper() == 'MPH':
        return "Master of Public Health"
    if text.upper() == 'MFA':
        return "Master of Fine Arts"
    
    # If no normalization needed, return as-is
    return text


def deduplicate_degrees(degrees: List[Dict]) -> List[Dict]:
    """
    Simple deduplication by normalized name.
    """
    seen = set()
    unique = []
    
    for deg in degrees:
        # Normalize for comparison
        name = deg['degree_name']
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Collapse whitespace
        normalized = normalized.replace('.', '').replace(',', '')
        
        if normalized not in seen:
            seen.add(normalized)
            unique.append(deg)
    
    return unique
