"""
Verification test: 30-50 program cap, graduate-only, c=15 t=6s config.
Run: .\venv\Scripts\python test_discovery.py
"""
import asyncio, sys, time, logging
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
# Show only program_discovery INFO for the stats we care about
logging.getLogger("pipeline.program_discovery").setLevel(logging.INFO)

from pipeline.domain_resolver import resolve_university_domain
from pipeline.program_discovery import discover_programs
from config import settings


async def test(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")
    t0 = time.monotonic()

    dr = await resolve_university_domain(name)
    domain = dr["domain"]
    print(f"  Domain : {domain}  (method={dr['method']})")

    if not domain:
        print("  FAILED: domain not resolved")
        return

    programs = await discover_programs(domain, name)
    elapsed = round(time.monotonic() - t0, 1)

    # Degree breakdown
    from collections import Counter
    levels = Counter(p["degree_level"] for p in programs)

    print(f"  Total  : {len(programs)} programs in {elapsed}s  (target: 30-50)")
    print(f"  Degrees: {dict(levels)}")

    # Flag actual undergrad contamination.
    # Graduate certificates (PGCE, grad certs) are valid output — don't flag them.
    # Only flag Bachelor's, Associate's, and certificates with "undergraduate" in name.
    undergrad_certs = [
        p for p in programs
        if p["degree_level"] == "Certificate"
        and any(w in p["program_name"].lower() for w in ["undergraduate", "ug cert", "associate"])
    ]
    bad = [p for p in programs if p["degree_level"] in ("Bachelor's", "Associate's")] + undergrad_certs
    if bad:
        print(f"  WARNING: {len(bad)} undergrad programs leaked through filter")
        for p in bad[:5]:
            print(f"      [{p['degree_level']}] {p['program_name']}")
    else:
        print(f"  OK Degree filter clean — no undergrad contamination")

    # Check cap
    cap = settings.max_programs_per_university
    if len(programs) <= cap:
        print(f"  ✅ Within cap ({len(programs)} <= {cap})")
    else:
        print(f"  ⚠️  OVER CAP: {len(programs)} > {cap}")

    # Show programs
    print(f"\n  Programs:")
    for p in programs:
        print(f"    [{p['degree_level']:12s}] {p['program_name']}")


async def main():
    await test("Arkansas State University")
    await test("University of Manchester")

asyncio.run(main())
