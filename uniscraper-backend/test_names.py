import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from pipeline.program_discovery import _auto_confirm_candidate, _normalize_url

async def test():
    cases = [
        "https://www.astate.edu/programs/ma-in-sociology.html",
        "https://www.astate.edu/programs/phd-in-heritage-studies.html",
        "https://www.astate.edu/programs/mba-in-marketing.html",
        "https://www.astate.edu/programs/ma-in-biology.xml",
        "https://www.manchester.ac.uk/study/masters/courses/list/09994/msc-business-psychology/",
        "https://www.manchester.ac.uk/study/postgraduate-research/programmes/list/05482/phd-mphil-astronomy-and-astrophysics/",
    ]
    for url in cases:
        r = await _auto_confirm_candidate(url, "")
        if r:
            print(f"  [{r['degree_level']:10s}] {r['program_name']}")
        else:
            print(f"  None: {url[-50:]}")

    # Dedup test
    print()
    print("Dedup test (html == xml):")
    n1 = _normalize_url("https://www.astate.edu/programs/ma-in-sociology.html")
    n2 = _normalize_url("https://www.astate.edu/programs/ma-in-sociology.xml")
    print(f"  html: {n1}")
    print(f"  xml:  {n2}")
    print(f"  match: {n1 == n2}")

asyncio.run(test())
