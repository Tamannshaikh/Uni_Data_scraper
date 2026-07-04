"""
Per-strategy extractors for different university page structures.

Each extractor:
1. Receives a BeautifulSoup container (scoped to main content)
2. Extracts degree names based on page structure
3. Returns list of {degree_name, url}

No scoring. No confidence. No classification. No LLM.
"""
import logging
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


# ============================================================================
# Utility: Degree detection
# ============================================================================

DEGREE_INDICATORS = [
    "master of", "master's", "m.s.", "m.a.", "m.sc.", "m.eng.", "m.arch.", 
    "m.f.a.", "m.p.h.", "m.phil.", "m.res.", "m.b.a.", "mba",
    "ms in", "ma in", "msc in", "meng",
    "phd", "ph.d", "ph.d.", "doctor of", "doctoral",
    "certificate", "graduate certificate",
    "j.d.", "ll.m.", "ed.d.", "d.n.p.", "aud", "mfa", "mph"
]

JUNK_PHRASES = [
    "admissions", "apply", "application", "overview", "about",
    "contact", "email", "phone", "home", "search", "menu",
    "tuition", "fees", "costs", "funding", "financial aid",
    "student support", "student life", "campus", "resources",
    "learn more", "read more", "view details", "more info",
    "news", "events", "faculty", "staff", "directory",
    "undergraduate", "bachelor",
    "why study", "why choose", "prospective",
    "download", "view all", "see all"
]


def looks_like_degree(text: str) -> bool:
    """Check if text looks like a degree name."""
    text_lower = text.lower().strip()
    
    # Too short or too long
    if len(text) < 8 or len(text) > 150:
        return False
    
    # Contains junk phrase
    if any(junk in text_lower for junk in JUNK_PHRASES):
        return False
    
    # Must contain degree indicator
    if not any(indicator in text_lower for indicator in DEGREE_INDICATORS):
        return False
    
    return True


def clean_degree_name(text: str) -> str:
    """Clean up degree name text."""
    text = text.strip()
    
    # Remove common suffixes
    for suffix in [' ›', ' »', ' >', ' →', ' *', ' (more info)', ' (apply)']:
        if text.endswith(suffix):
            text = text[:-len(suffix)].strip()
    
    return text


# ============================================================================
# Strategy 1: Anchor extraction (degree names in <a> tag text)
# ============================================================================

def extract_anchor(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from anchor tags.
    
    Used when: Degree names ARE the anchor text.
    Example: <a href="/program/ms-cs">MS Computer Science</a>
    """
    programs = []
    seen_urls = set()
    
    for link in container.find_all('a', href=True):
        href = link.get('href', '').strip()
        if not href or href.startswith('#'):
            continue
        
        # Make absolute URL
        absolute_url = urljoin(base_url, href)
        
        # Skip duplicates
        if absolute_url in seen_urls:
            continue
        
        # Get anchor text
        text = link.get_text(strip=True)
        
        # Check if looks like degree
        if not looks_like_degree(text):
            continue
        
        degree_name = clean_degree_name(text)
        seen_urls.add(absolute_url)
        
        programs.append({
            'degree_name': degree_name,
            'url': absolute_url
        })
    
    logger.info(f"[extract_anchor] Found {len(programs)} programs")
    return programs


# ============================================================================
# Strategy 2: List text extraction (degree names in <li> text)
# ============================================================================

def extract_list_text(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from list item text OR table cells.
    
    Used when: Degree names are in <li>, <p>, or <td> text, not necessarily in anchors.
    Example: <li>Aeronautics and Astronautics Fields (PhD)</li>
              <td>Computer Science</td>
    """
    programs = []
    seen_names = set()
    
    # Try table cells first (for MIT-style tables)
    for cell in container.find_all('td'):
        text = cell.get_text(strip=True)
        
        if not looks_like_degree(text):
            continue
        
        degree_name = clean_degree_name(text)
        normalized = degree_name.lower()
        
        if normalized in seen_names:
            continue
        
        seen_names.add(normalized)
        
        # Try to find a link within or near this cell
        link = cell.find('a', href=True)
        url = urljoin(base_url, link['href']) if link else base_url
        
        programs.append({
            'degree_name': degree_name,
            'url': url
        })
    
    # Try list items
    for item in container.find_all(['li', 'p']):
        text = item.get_text(strip=True)
        
        if not looks_like_degree(text):
            continue
        
        degree_name = clean_degree_name(text)
        normalized = degree_name.lower()
        
        if normalized in seen_names:
            continue
        
        seen_names.add(normalized)
        
        # Try to find a link within or near this item
        link = item.find('a', href=True)
        url = urljoin(base_url, link['href']) if link else base_url
        
        programs.append({
            'degree_name': degree_name,
            'url': url
        })
    
    logger.info(f"[extract_list_text] Found {len(programs)} programs")
    return programs


# ============================================================================
# Strategy 3: Heading extraction (degree names in <h2>/<h3>)
# ============================================================================

def extract_heading(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from heading tags.
    
    Used when: Degree names or program names are in <h2> or <h3> headings.
    Example: <h2>MS in Computer Science</h2>
              <h2>Computer Science</h2> (Purdue-style)
    
    For Purdue: looks specifically for <div class="program-card"> containers.
    Less strict - accepts program names without explicit degree keywords.
    """
    programs = []
    seen_names = set()
    
    # Try Purdue-style first: program-card divs (class can be program-card or program-cards)
    program_cards = container.find_all('div', class_=lambda x: x and ('program-card' in ' '.join(x) if isinstance(x, list) else 'program-card' in x))
    
    logger.info(f"[extract_heading] Checking for program-card divs: found {len(program_cards)}")
    
    if program_cards:
        for card in program_cards:
            heading = card.find(['h2', 'h3'])
            if not heading:
                continue
            
            text = heading.get_text(strip=True)
            
            # Basic sanity checks
            if len(text) < 3 or len(text) > 150:
                continue
            
            text_lower = text.lower()
            
            # Filter junk
            if any(junk in text_lower for junk in JUNK_PHRASES):
                continue
            
            degree_name = clean_degree_name(text)
            normalized = degree_name.lower()
            
            if normalized in seen_names:
                continue
            
            seen_names.add(normalized)
            
            # Find link in this card
            link = card.find('a', href=True)
            url = urljoin(base_url, link['href']) if link else base_url
            
            programs.append({
                'degree_name': degree_name,
                'url': url
            })
        
        logger.info(f"[extract_heading] Found {len(programs)} programs from program-card divs")
        return programs
    
    # Fallback: generic H2/H3 extraction
    for heading in container.find_all(['h2', 'h3', 'h4']):
        text = heading.get_text(strip=True)
        
        # Basic sanity checks
        if len(text) < 3 or len(text) > 150:
            continue
        
        text_lower = text.lower()
        
        # Filter obvious junk
        if any(junk in text_lower for junk in JUNK_PHRASES):
            continue
        
        # Skip navigation/UI elements
        if any(word in text_lower for word in ['icon', 'menu', 'follow', 'explore', 'information', 'communication', 'need help']):
            continue
        
        degree_name = clean_degree_name(text)
        normalized = degree_name.lower()
        
        if normalized in seen_names:
            continue
        
        seen_names.add(normalized)
        
        # Try to find a link near this heading
        link = heading.find_next('a', href=True)
        url = urljoin(base_url, link['href']) if link else base_url
        
        programs.append({
            'degree_name': degree_name,
            'url': url
        })
    
    logger.info(f"[extract_heading] Found {len(programs)} programs")
    return programs


# ============================================================================
# Strategy 4: Heading with button (degree in heading, link in button)
# ============================================================================

def extract_heading_with_button(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from heading + button pattern.
    
    Used when: Degree name in heading, "MORE INFO" button has the actual link.
    Example:
        <section>
            <h2>MS in Computer Science</h2>
            <a href="/programs/cs">MORE INFO</a>
        </section>
    
    For Purdue-style pages where H2 contains program name without explicit
    degree type (e.g. "Computer Science" not "MS in Computer Science").
    """
    programs = []
    seen_names = set()
    
    # Find all headings (H2 for Purdue)
    for heading in container.find_all(['h2', 'h3']):
        text = heading.get_text(strip=True)
        
        # Skip if too short or contains junk
        if len(text) < 3 or len(text) > 150:
            continue
        
        text_lower = text.lower()
        if any(junk in text_lower for junk in JUNK_PHRASES):
            continue
        
        # For Purdue-style: accept program names even without explicit degree words
        # But still filter obvious non-programs
        degree_name = clean_degree_name(text)
        normalized = degree_name.lower()
        
        if normalized in seen_names:
            continue
        
        # Find the closest parent container (section, div, article)
        parent = heading.find_parent(['section', 'div', 'article'])
        if not parent:
            parent = heading.parent
        
        # Find "MORE INFO" or similar button within parent
        info_button = None
        if parent:
            info_button = parent.find(
                'a',
                href=True,
                string=lambda x: x and any(
                    keyword in x.upper() 
                    for keyword in ['MORE INFO', 'ADMISSION', 'LEARN MORE', 'DETAILS', 'VIEW']
                )
            )
        
        # If no button found, look for any link in parent
        if not info_button and parent:
            info_button = parent.find('a', href=True)
        
        if not info_button:
            continue
        
        # If there's a button, accept this as a program
        url = urljoin(base_url, info_button['href'])
        
        seen_names.add(normalized)
        
        programs.append({
            'degree_name': degree_name,
            'url': url
        })
    
    logger.info(f"[extract_heading_with_button] Found {len(programs)} programs")
    return programs


# ============================================================================
# Strategy 5: Table extraction (degrees in table cells)
# ============================================================================

def extract_table(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from table cells.
    
    Used when: Degree names are in table cells (typically first column).
    Example: MIT's fields of study page with program names in first column.
    
    MIT-specific: Each linked row in the table is a program. Section headers 
    are bold with no links. Accept all rows with links except "Program" header.
    """
    programs = []
    seen_names = set()
    
    for table in container.find_all('table'):
        for row in table.find_all('tr'):
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            first_cell = cells[0]
            
            # MIT pattern: programs have links, section headers don't
            link = first_cell.find('a', href=True)
            if not link:
                continue  # Skip section headers and header row
            
            text = first_cell.get_text(' ', strip=True)
            
            # Skip header row if it says "Program"
            if text == 'Program' or text == 'Field' or text == 'Department':
                continue
            
            # Skip if too short/long
            if len(text) < 3 or len(text) > 150:
                continue
            
            text_lower = text.lower()
            
            # Filter obvious junk (shouldn't be in MIT's table but defensive)
            if any(junk in text_lower for junk in ['apply', 'contact', 'search', 'menu', 'download']):
                continue
            
            degree_name = clean_degree_name(text)
            normalized = degree_name.lower()
            
            if normalized in seen_names:
                continue
            
            seen_names.add(normalized)
            
            url = urljoin(base_url, link['href'])
            
            programs.append({
                'degree_name': degree_name,
                'url': url
            })
    
    logger.info(f"[extract_table] Found {len(programs)} programs")
    return programs


# ============================================================================
# Strategy 6: Plain text list (no individual URLs)
# ============================================================================

def extract_plain_text_list(base_url: str, container: BeautifulSoup) -> List[Dict]:
    """
    Extract degrees from plain text lists.
    
    Used when: Degrees are listed as plain text bullets without individual links.
    Example: <li>Anthropology PhD</li> (no link, just text)
    
    Returns catalog URL for all programs since no individual links exist.
    """
    programs = []
    seen_names = set()
    
    for item in container.find_all(['li', 'p']):
        text = item.get_text(strip=True)
        
        if not looks_like_degree(text):
            continue
        
        degree_name = clean_degree_name(text)
        normalized = degree_name.lower()
        
        if normalized in seen_names:
            continue
        
        seen_names.add(normalized)
        
        # No individual URL - use catalog page
        programs.append({
            'degree_name': degree_name,
            'url': base_url
        })
    
    logger.info(f"[extract_plain_text_list] Found {len(programs)} programs")
    return programs


# ============================================================================
# Extractor dispatcher
# ============================================================================

EXTRACTORS = {
    "anchor": extract_anchor,
    "list_text": extract_list_text,
    "heading": extract_heading,
    "heading_with_button": extract_heading_with_button,
    "table": extract_table,
    "plain_text_list": extract_plain_text_list,
}


def extract_programs(
    strategy: str,
    base_url: str,
    html: str
) -> List[Dict]:
    """
    Extract programs using specified strategy.
    
    Args:
        strategy: Extraction strategy name
        base_url: Base URL for making absolute links
        html: HTML content
    
    Returns:
        List of {degree_name, url}
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Scope to main content container
    container = (
        soup.find('main') or 
        soup.find('article') or 
        soup.find('section') or
        soup.find('div', {'id': 'content'}) or
        soup.find('div', {'class': 'content'}) or
        soup
    )
    
    # Debug logging for Purdue
    if 'purdue.edu' in base_url:
        logger.info(f"[extractors] Container type: {container.name if container else 'None'}")
        logger.info(f"[extractors] Container has {len(container.find_all('div'))} divs")
        test_cards = container.find_all('div', class_='program-card')
        logger.info(f"[extractors] Test: program-card divs = {len(test_cards)}")
    
    logger.info(f"[extractors] Using strategy '{strategy}' on {base_url[:60]}")
    
    extractor = EXTRACTORS.get(strategy)
    if not extractor:
        logger.error(f"[extractors] Unknown strategy: {strategy}")
        return []
    
    return extractor(base_url, container)


def deduplicate_programs(programs: List[Dict]) -> List[Dict]:
    """Remove duplicate programs by normalized name."""
    seen = set()
    unique = []
    
    for prog in programs:
        normalized = prog['degree_name'].lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(prog)
    
    return unique
