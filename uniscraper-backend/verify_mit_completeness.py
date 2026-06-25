"""
Verify MIT extraction is complete by fetching raw HTML and checking table structure.
"""
import asyncio
import httpx
from bs4 import BeautifulSoup

async def check_mit():
    url = "https://oge.mit.edu/graduate-admissions/programs/fields-of-study/"
    
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(url)
        html = resp.text
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find main
    main = soup.find('main')
    if not main:
        print("❌ No <main> found")
        return
    
    # Find all tables
    tables = main.find_all('table')
    print(f"Found {len(tables)} tables in <main>")
    
    for i, table in enumerate(tables, 1):
        print(f"\n{'='*80}")
        print(f"TABLE {i}")
        print(f"{'='*80}")
        
        rows = table.find_all('tr')
        print(f"Rows: {len(rows)}")
        
        for j, row in enumerate(rows, 1):  # ALL rows
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            first_cell_text = cells[0].get_text(' ', strip=True)
            has_link = bool(cells[0].find('a', href=True))
            is_bold = bool(cells[0].find(['strong', 'b']))
            
            print(f"  Row {j}: [{('LINK' if has_link else '----')}] [{('BOLD' if is_bold else '----')}] {first_cell_text[:80]}")

asyncio.run(check_mit())
