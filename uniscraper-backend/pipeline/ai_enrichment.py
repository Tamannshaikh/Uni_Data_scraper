# pipeline/ai_enrichment.py
# AI Enrichment Pass — fills missing fields via direct AI inference.
#
# Called AFTER the main extraction pipeline when high-value fields are still null.
# Uses Gemini's general knowledge to infer typical values for the program.
# Results are clearly tagged with * so the frontend can show they're AI-generated.
#
# SAFE fields (AI can enrich):
#   ✅ program_duration, intake_months, application_deadlines
#   ✅ english_requirements (ielts/toefl/pte/duolingo), min_academic_requirement
#   ✅ accepted_qualifications, work_experience
#
# UNSAFE fields (never fill with AI — must come from official source):
#   ❌ tuition_fees, scholarships, other_fees (money amounts must be exact)
#   ❌ university_name, program_name, degree_level (identity must be scraped)
#
# Official scraped values are NEVER overwritten. AI only fills null fields.

import asyncio
import json
import logging
import re
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Fields safe for AI enrichment
AI_ENRICHABLE_FIELDS = [
    "program_duration",
    "intake_months",
    "application_deadlines",
    "min_academic_requirement",
    "accepted_qualifications",
    "work_experience",
]

# Sub-fields in english_requirements safe for AI enrichment
AI_ENRICHABLE_ENGLISH_SUBFIELDS = ["ielts", "toefl", "pte", "duolingo"]

# Gemini API URL
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={api_key}"
)


def _get_missing_fields(extracted: dict) -> dict:
    """
    Returns dict of {field_name: True} for fields safe to AI-enrich that are null.
    Also checks english_requirements sub-fields.
    """
    missing = {}

    for field in AI_ENRICHABLE_FIELDS:
        val = extracted.get(field)
        if val is None or val == [] or val == "":
            missing[field] = True

    # Check english sub-fields
    eng = extracted.get("english_requirements") or {}
    if isinstance(eng, dict):
        eng_missing = [f for f in AI_ENRICHABLE_ENGLISH_SUBFIELDS if not eng.get(f)]
        if eng_missing:
            missing["english_requirements"] = eng_missing  # list of missing sub-fields

    return missing


def _build_json_schema(missing: dict) -> str:
    """Build the expected JSON return schema based on what's missing."""
    schema = {}
    for field, val in missing.items():
        if field == "english_requirements":
            schema["english_requirements"] = {sub: None for sub in val}
        elif field == "intake_months":
            schema[field] = None  # JSON array of month names, or null
        else:
            schema[field] = None
    return json.dumps(schema, indent=2)


async def _call_gemini_for_missing_fields(
    university_name: str,
    program_name: str,
    missing: dict
) -> Optional[dict]:
    """
    Ask Gemini directly for missing fields using its general knowledge.
    No web search - just AI inference from training data.
    
    Returns dict of inferred values or None if Gemini fails.
    """
    if not settings.gemini_api_key:
        logger.warning("[ai_enrichment] No GEMINI_API_KEY configured")
        return None

    # Build field descriptions for the prompt
    field_descriptions = []
    for field, val in missing.items():
        if field == "english_requirements":
            subfields = ', '.join(val) if isinstance(val, list) else "all"
            field_descriptions.append(f"- english_requirements ({subfields}): typical IELTS/TOEFL/PTE/Duolingo scores")
        elif field == "program_duration":
            field_descriptions.append("- program_duration: typical length (e.g., '2 years', '12 months')")
        elif field == "intake_months":
            field_descriptions.append("- intake_months: typical start months (JSON array like [\"September\", \"January\"])")
        elif field == "application_deadlines":
            field_descriptions.append("- application_deadlines: typical deadline dates")
        elif field == "work_experience":
            field_descriptions.append("- work_experience: whether work experience is typically required")
        else:
            field_descriptions.append(f"- {field}: typical value")
    
    missing_fields_text = "\n".join(field_descriptions)
    json_schema = _build_json_schema(missing)

    prompt = f"""You are helping fill missing university program data using your general knowledge.

University: {university_name}
Program: {program_name}

Missing fields to infer:
{missing_fields_text}

RULES:
1. Use ONLY your general knowledge of this university and program type
2. Return values ONLY if reasonably confident based on typical requirements
3. If unsure or no knowledge, return null for that field
4. Never invent exact fees, rankings, or scholarship amounts
5. For English requirements, use typical official requirements only
6. For deadlines, use typical application cycles if you know them
7. Keep responses concise - just the values

Return ONLY valid JSON matching this schema (null for anything unknown):
{json_schema}"""

    try:
        logger.info(f"[ai_enrichment] Asking Gemini directly for {len(missing)} missing fields")
        
        url = _GEMINI_URL.format(
            model="gemini-2.5-flash",
            api_key=settings.gemini_api_key,
        )
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("```").strip()
        result = json.loads(text)
        
        logger.info(f"[ai_enrichment] Gemini provided values for fields: {list(result.keys())}")
        return result
        
    except Exception as e:
        logger.warning(f"[ai_enrichment] Gemini enrichment failed: {type(e).__name__}: {e}")
        return None


async def run_ai_enrichment(
    extracted: dict,
    final_url: str,
) -> tuple[dict, dict]:
    """
    Main enrichment entry point.

    Args:
        extracted: The extraction result dict (after Pass 1 + Pass 2)
        final_url: The program URL (used for context)

    Returns:
        (enriched_extracted, ai_generated_fields)
        - enriched_extracted: updated dict with null fields filled where found
        - ai_generated_fields: {field_name: True} for every field filled by AI
          (used by frontend to show * marker)
    """
    university_name = extracted.get("university_name") or ""
    program_name = extracted.get("program_name") or ""

    if not university_name or not program_name:
        logger.info("[ai_enrichment] Skipping — no university/program name available")
        return extracted, {}

    missing = _get_missing_fields(extracted)
    if not missing:
        logger.info("[ai_enrichment] No enrichable fields missing — skipping")
        return extracted, {}

    logger.info(f"[ai_enrichment] Missing enrichable fields: {list(missing.keys())}")

    # ── Ask Gemini directly for missing fields ────────────────────────────────
    ai_result = await _call_gemini_for_missing_fields(university_name, program_name, missing)
    if not ai_result:
        logger.info("[ai_enrichment] No AI result returned")
        return extracted, {}

    # ── Merge: official values always win, AI only fills nulls ───────────────
    ai_generated_fields: dict = {}
    enriched = dict(extracted)

    for field, ai_val in ai_result.items():
        if ai_val is None:
            continue

        if field == "english_requirements":
            # Merge sub-fields into existing english_requirements dict
            if not isinstance(ai_val, dict):
                continue
            existing_eng = enriched.get("english_requirements") or {}
            if not isinstance(existing_eng, dict):
                existing_eng = {}
            changed = False
            for sub_field, sub_val in ai_val.items():
                if sub_val and not existing_eng.get(sub_field):
                    # Add * to mark as AI-generated
                    if isinstance(sub_val, str) and not sub_val.endswith("*"):
                        sub_val = sub_val + "*"
                    existing_eng[sub_field] = sub_val
                    ai_generated_fields[f"english_requirements.{sub_field}"] = True
                    changed = True
                    logger.info(f"[ai_enrichment] ✅ english_requirements.{sub_field} = {sub_val}")
            if changed:
                enriched["english_requirements"] = existing_eng
        else:
            # Only fill if currently null — never overwrite scraped values
            if not enriched.get(field):
                # Convert boolean work_experience to user-friendly text
                if field == "work_experience":
                    if ai_val is False:
                        ai_val = "Not required*"
                    elif ai_val is True:
                        ai_val = "Required*"
                    elif isinstance(ai_val, str) and not ai_val.endswith("*"):
                        ai_val = ai_val + "*"
                # Add * to mark as AI-generated
                elif isinstance(ai_val, str) and not ai_val.endswith("*"):
                    ai_val = ai_val + "*"
                elif isinstance(ai_val, list):
                    # For lists, add * to each string item
                    ai_val = [item + "*" if isinstance(item, str) and not item.endswith("*") else item for item in ai_val]
                
                enriched[field] = ai_val
                ai_generated_fields[field] = True
                logger.info(f"[ai_enrichment] ✅ {field} = {ai_val}")
            else:
                logger.debug(f"[ai_enrichment] skipping {field} — already has official value")

    # ── Add disclaimer note if any fields were AI-generated ───────────────────
    if ai_generated_fields:
        # Check if any enriched value contains *
        contains_ai_marker = False
        for key, value in enriched.items():
            if isinstance(value, str) and "*" in value:
                contains_ai_marker = True
                break
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and "*" in item:
                        contains_ai_marker = True
                        break
            elif isinstance(value, dict):
                for sub_val in value.values():
                    if isinstance(sub_val, str) and "*" in sub_val:
                        contains_ai_marker = True
                        break
        
        if contains_ai_marker:
            enriched["ai_generated_fields_note"] = (
                "Fields marked with * were inferred by AI and may not be accurate. "
                "Please verify important details on the official university website."
            )
            logger.info("[ai_enrichment] Added AI-generated fields disclaimer")
        
        logger.info(
            f"[ai_enrichment] Enriched {len(ai_generated_fields)} fields: "
            f"{list(ai_generated_fields.keys())}"
        )
    else:
        logger.info("[ai_enrichment] AI found nothing new to add")

    return enriched, ai_generated_fields
