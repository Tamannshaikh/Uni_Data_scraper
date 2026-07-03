#!/usr/bin/env python3
"""
Manually inspect UCLA's actual program listing to understand structure.
"""
import asyncio
import httpx
from bs4 import BeautifulSoup


async def test_url(url: str, name: str):
    """Test a specific UCLA URL."""
    print(f"\n{'='*80}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")
    
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    ) as client:
        response = await client.get(url)
        
        print(f"Status: {response.status_code}")
        print(f"Length: {len(response.text)} chars\n")
        
        if response.status_code == 200:
            html = response.text
            soup = BeautifulSoup(html, 'lxml')
            
            # Find links with degree keywords
            links = soup.find_all('a', href=True)
            program_links = []
            
            for link in links:
                text = link.get_text(' ', strip=True)
                if len(text) > 15 and ('master' in text.lower() or 'phd' in text.lower() or 'doctor' in text.lower()):
                    program_links.append({
                        'text': text,
                        'href': link['href']
                    })
            
            print(f"Links with degree keywords: {len(program_links)}\n")
            
            if program_links:
                print("Sample program links:")
                for i, prog in enumerate(program_links[:10], 1):
                    print(f"{i:2d}. {prog['text']}")
                    print(f"    {prog['href']}\n")
            else:
                print("No program links found")
                print("\nAll links on page:")
                for i, link in enumerate(links[:20], 1):
                    text = link.get_text(' ', strip=True)[:60]
                    href = link.get('href', '')[:60]
                    print(f"{i:2d}. {text} -> {href}")


async def main():
    """Test various UCLA URLs."""
    urls = [
        ("https://grad.ucla.edu/programs/", "Graduate Programs Directory"),
        ("https://grad.ucla.edu/academics/masters-studies", "Master's Studies Page"),
        ("https://www.ucla.edu/academics/programs-and-majors", "Programs and Majors"),
    ]
    
    for url, name in urls:
        await test_url(url, name)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
