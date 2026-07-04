"""
University-Specific Adapters

For universities that require custom extraction logic.
This is the 5% exception to the 95% generic pipeline.
"""
import asyncio
import logging
from typing import List, Dict
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def extract_stanford() -> List[Dict]:
    """
    Stanford adapter - uses Playwright to render dynamic program portal.
    
    URL: https://applygrad.stanford.edu/portal/programs
    
    The page is JavaScript-rendered, generic static extraction fails.
    """
    try:
        from playwright.async_api import async_playwright
        
        url = "https://applygrad.stanford.edu/portal/programs"
        
        logger.info(f"[stanford_adapter] Using Playwright to render {url}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)  # Let JS finish
            
            content = await page.content()
            await browser.close()
            
            logger.info(f"[stanford_adapter] Rendered page: {len(content)} chars")
            
            # Extract from rendered HTML
            from pipeline.catalog_url_guesser import extract_degrees_from_catalog
            degrees = await extract_degrees_from_catalog(url, content, use_playwright=False)
            
            logger.info(f"[stanford_adapter] Extracted {len(degrees)} degrees")
            return degrees
    
    except Exception as e:
        logger.error(f"[stanford_adapter] Failed: {e}")
        return []


async def extract_purdue() -> List[Dict]:
    """
    Purdue adapter - extracts from online programs page with strict filtering.
    
    URL: https://www.purdue.edu/online/programs-of-study/
    
    Problem: Page has many links, need to filter carefully.
    """
    try:
        url = "https://www.purdue.edu/online/programs-of-study/"
        
        logger.info(f"[purdue_adapter] Fetching {url}")
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if resp.status_code != 200:
                logger.error(f"[purdue_adapter] HTTP {resp.status_code}")
                return []
            
            # Use strict extraction (headings/lists only)
            from pipeline.catalog_url_guesser import extract_degrees_from_catalog
            degrees = await extract_degrees_from_catalog(url, resp.text, use_playwright=False)
            
            # Additional filtering for Purdue
            filtered = []
            for deg in degrees:
                name = deg['degree_name']
                
                # Reject if too generic
                if name.lower() in ['master of science', 'doctor of philosophy', 'ms', 'phd']:
                    continue
                
                # Reject if contains sentence indicators
                if any(word in name.lower() for word in ['designed', 'prepares', 'provides', 'offers']):
                    continue
                
                filtered.append(deg)
            
            logger.info(f"[purdue_adapter] Extracted {len(filtered)} degrees (filtered from {len(degrees)})")
            return filtered
    
    except Exception as e:
        logger.error(f"[purdue_adapter] Failed: {e}")
        return []


async def extract_cmu() -> List[Dict]:
    """
    CMU adapter - follows deep navigation structure.
    
    URL: https://www.cmu.edu/graduate/programs/index.html
    
    Problem: Programs are nested deep in department pages.
    """
    try:
        base_url = "https://www.cmu.edu/graduate/programs/index.html"
        
        logger.info(f"[cmu_adapter] Fetching {base_url}")
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
            
            if resp.status_code != 200:
                logger.error(f"[cmu_adapter] HTTP {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find all program/degree links
            program_urls = set()
            
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True).lower()
                
                # Look for program-related links
                if any(keyword in text for keyword in ['master', 'phd', 'doctor', 'ms', 'ma', 'mba']):
                    if href.startswith('http'):
                        program_urls.add(href)
                    elif href.startswith('/'):
                        program_urls.add(f"https://www.cmu.edu{href}")
            
            logger.info(f"[cmu_adapter] Found {len(program_urls)} program URLs, following...")
            
            # Extract from each program page
            all_degrees = []
            
            for url in list(program_urls)[:30]:  # Limit to 30 pages
                try:
                    page_resp = await client.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10.0)
                    if page_resp.status_code == 200:
                        from pipeline.catalog_url_guesser import extract_degrees_from_catalog
                        degrees = await extract_degrees_from_catalog(url, page_resp.text, use_playwright=False)
                        
                        if degrees:
                            logger.debug(f"[cmu_adapter] Found {len(degrees)} degrees at {url[:60]}")
                            all_degrees.extend(degrees)
                
                except Exception as e:
                    logger.debug(f"[cmu_adapter] Failed to fetch {url[:60]}: {e}")
                    continue
            
            logger.info(f"[cmu_adapter] Extracted {len(all_degrees)} total degrees")
            
            # Deduplicate
            seen = set()
            unique = []
            for deg in all_degrees:
                normalized = deg['degree_name'].lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    unique.append(deg)
            
            logger.info(f"[cmu_adapter] {len(unique)} unique degrees after deduplication")
            return unique
    
    except Exception as e:
        logger.error(f"[cmu_adapter] Failed: {e}")
        return []


# Registry of special handlers
SPECIAL_HANDLERS = {
    "stanford.edu": extract_stanford,
    "purdue.edu": extract_purdue,
    "cmu.edu": extract_cmu,
}
