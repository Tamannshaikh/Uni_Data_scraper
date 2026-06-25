"""
Test all 4 configured universities with full output display.

Validates:
- MIT (table strategy)
- Purdue (heading strategy)
- Arkansas (anchor strategy) 
- UCSD (plain_text_list strategy)

Prints EVERY extracted item for manual verification.
"""
import asyncio
import logging
from pipeline.fetcher import fetch_page
from pipeline.extractors import extract_programs
from UNIVERSITY_CONFIG import UNIVERSITY_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_university(domain: str, config: dict):
    """Test a single university and print all extracted programs."""
    print("\n" + "="*80)
    print(f"Testing: {domain}")
    print(f"URL: {config['url']}")
    print(f"Strategy: {config['strategy']}")
    print("="*80)
    
    # Fetch page
    result = await fetch_page(config['url'])
    
    if not result.get('html'):
        print(f"❌ FETCH FAILED: {result.get('error', 'Unknown error')}")
        return
    
    print(f"✓ Fetched {len(result['html'])} bytes via {result.get('method_used', 'unknown')}")
    
    # Extract programs
    programs = extract_programs(
        strategy=config['strategy'],
        base_url=config['url'],
        html=result['html']
    )
    
    print(f"\n{'='*80}")
    print(f"RESULTS: Found {len(programs)} programs")
    print(f"{'='*80}")
    
    if not programs:
        print("❌ NO PROGRAMS EXTRACTED")
        return
    
    # Print every single item
    for i, prog in enumerate(programs, 1):
        print(f"{i:3d}. {prog['degree_name']}")
    
    print(f"\n{'='*80}")
    print(f"MANUAL VERIFICATION REQUIRED:")
    print(f"- Are ALL {len(programs)} items real degree/program names?")
    print(f"- Any deadline text, nav menus, or junk?")
    print(f"{'='*80}")


async def main():
    """Test all 4 universities."""
    # Test in order: working → problematic
    domains = [
        "uark.edu",      # Working (Arkansas)
        "ucsd.edu",      # Working (UCSD)
        "mit.edu",       # Needs fix (currently 60% precision)
        "purdue.edu",    # Needs fix (currently 0 programs)
    ]
    
    for domain in domains:
        config = UNIVERSITY_CONFIG.get(domain)
        if not config:
            print(f"\n❌ {domain} not configured")
            continue
        
        try:
            await test_university(domain, config)
        except Exception as e:
            print(f"\n❌ {domain} EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
