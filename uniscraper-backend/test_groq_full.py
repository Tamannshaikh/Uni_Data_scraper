"""
Full discovery test using Groq only (for when Gemini quota is exhausted).
Patches out the Gemini call to fail immediately, forcing full Groq fallback path.
Run: .\venv\Scripts\python test_groq_full.py
"""
import asyncio, sys, time, logging
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
logging.getLogger("pipeline.program_discovery").setLevel(logging.INFO)

# Patch Gemini to immediately return [] (simulate quota exhaustion without waiting 30s)
import pipeline.program_discovery as pd_module

_original_call_gemini = pd_module._call_gemini_classify

async def _mock_gemini_unavailable(candidates):
    """Simulate instant Gemini quota failure — no 30s wait."""
    logging.getLogger("pipeline.program_discovery").warning(
        "[TEST] Gemini mocked as unavailable — routing to Groq"
    )
    return []

pd_module._call_gemini_classify = _mock_gemini_unavailable

from pipeline.domain_resolver import resolve_university_domain
from pipeline.program_discovery import discover_programs
from config import settings


async def test(name: str):
    print(f"\n{'='*60}")
    print(f"  {name}  [Groq-only mode]")
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

    from collections import Counter
    levels = Counter(p["degree_level"] for p in programs)

    print(f"  Total  : {len(programs)} programs in {elapsed}s")
    print(f"  Degrees: {dict(levels)}")

    bad = [p for p in programs if p["degree_level"] in ("Bachelor's", "Associate's")]
    if bad:
        print(f"  WARNING: {len(bad)} undergrad programs leaked through")
    else:
        print(f"  OK: No undergrad contamination")

    cap = settings.max_programs_per_university
    print(f"  {'OK' if len(programs) <= cap else 'WARNING'}: {len(programs)}/{cap} cap")

    cert_count = sum(1 for p in programs if p["degree_level"] == "Certificate")
    degree_total = sum(1 for p in programs if p["degree_level"] in ("PhD", "Doctoral", "Master's", "MBA"))
    print(f"  {'OK' if cert_count <= degree_total else 'WARNING'}: Degrees={degree_total} Certs={cert_count}")

    print(f"\n  Programs:")
    for p in programs:
        print(f"    [{p['degree_level']:12s}] {p['program_name']}")


async def main():
    await test("Arkansas State University")
    # Skip Manchester — it's all slug auto-confirmed, no Gemini needed anyway


asyncio.run(main())
