#!/usr/bin/env python3
"""
Test ASU program extraction to see why we're getting 0 results.
"""
import asyncio
import httpx
from bs4 import BeautifulSoup
import re


async def test_asu_extraction():
    """Test extracting programs from ASU catalog page."""
    url = "https://degrees.apps.asu.edu/masters-phd/major-list/letter/all"
    
    print(f"Fetching: {url}\n")
    
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    ) as client:
        response = await client.get(url)
        
        print(f"Status: {response.status_code}")
        print(f"Content length: {len(response.text)} chars\n")
        
        html = response.text
        soup = BeautifulSoup(html, 'lxml')
        
        # Find all links
        all_links = soup.find_all('a', href=True)
        print(f"Total links found: {len(all_links)}\n")
        
        # Look for program patterns
        program_links = []
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(' ', strip=True)
            
            # Check if it looks like a program
            if 'master' in text.lower() or 'phd' in text.lower() or 'doctor' in text.lower():
                program_links.append({
                    'text': text,
                    'href': href
                })
        
        print(f"Links with degree keywords: {len(program_links)}\n")
        
        # Show first 20
        print("Sample program links:")
        print("="*80)
        for i, prog in enumerate(program_links[:20], 1):
            print(f"{i:2d}. {prog['text']}")
            print(f"    {prog['href']}\n")
        
        # Check URL structure
        print("\n" + "="*80)
        print("URL STRUCTURE ANALYSIS:")
        print("="*80)
        
        # Group by URL pattern
        url_patterns = {}
        for prog in program_links:
            href = prog['href']
            if '/masters-phd/major/' in href:
                key = '/masters-phd/major/'
            elif '/masters-phd/' in href:
                key = '/masters-phd/ (other)'
            else:
                key = 'other'
            
            url_patterns[key] = url_patterns.get(key, 0) + 1
        
        for pattern, count in sorted(url_patterns.items(), key=lambda x: -x[1]):
            print(f"{pattern}: {count} programs")


if __name__ == "__main__":
    asyncio.run(test_asu_extraction())
