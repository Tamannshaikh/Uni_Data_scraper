"""
Check what content was sent to Gemini for obviously-program pages that were rejected
"""
import asyncio
from pipeline.program_discovery import _fetch_html, _get_title, _get_snippet

async def check():
    urls = [
        'https://business.purdue.edu/phd/',
        'https://business.purdue.edu/masters/',
    ]
    for url in urls:
        html, status = await _fetch_html(url, timeout=8.0)
        title = _get_title(html)
        snippet = _get_snippet(html, max_words=200)
        print(f'\n{"="*80}')
        print(f'URL: {url}')
        print(f'Status: {status}')
        print(f'Title: {title}')
        print(f'Snippet length: {len(snippet)} chars')
        print(f'Snippet (first 500 chars): {snippet[:500]}...')
        print(f'Full snippet: {snippet}')
        print()

asyncio.run(check())
