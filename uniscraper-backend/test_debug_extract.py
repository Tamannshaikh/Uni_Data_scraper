"""Debug: find the real programs listing page for Arkansas State."""
import asyncio
from pipeline.program_discovery import _fetch_html, _word_count, _get_title

async def test():
    urls_to_check = [
        "https://www.astate.edu/programs/",
        "https://www.astate.edu/programs/index.html",
        "https://www.astate.edu/academics/graduate-school/",
        "https://www.astate.edu/admissions-and-aid/graduate-admissions/",
        "https://www.astate.edu/admissions-and-aid/graduate-admissions/index.html",
    ]
    
    for url in urls_to_check:
        html, status = await _fetch_html(url)
        title = _get_title(html)
        # Count actual program links
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        prog_links = [a["href"] for a in soup.find_all("a", href=True) 
                      if "/programs/" in a["href"] and a["href"].endswith(".html")]
        print(f"{status} | {_word_count(html):5d}w | {len(prog_links):3d} prog links | {title[:50]} | {url}")

asyncio.run(test())
