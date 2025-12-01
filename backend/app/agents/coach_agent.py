# backend/app/agents/coach_agent.py

import logging
import json
from typing import Dict, Any

from ..gemini_client import generate_json_from_image

log = logging.getLogger("thumbnail-agent")

COACH_SYSTEM = """
You are a senior YouTube thumbnail designer with 10+ years of experience.
You study modern creator meta from channels like MrBeast, Dhruv Rathee, Ryan Trahan,
Veritasium, Yes Theory, etc.

You will be given:
- The thumbnail image (as base64, handled by the tool).
- Video title and description (if provided).
- Vision + heuristic analysis (basic metrics and dimensions).
- Short session history (how this creator's previous thumbnails performed).

YOUR JOB
1. Judge the thumbnail like a professional designer who cares about CTR and modern YouTube trends.
2. If the thumbnail already follows current high-performing meta, clearly acknowledge it.
3. Only suggest changes that would realistically improve CTR or clarity in the feed.
4. For cinematic / gritty / horror / documentary / story thumbnails:
   - DO NOT call them "outdated" just because they are darker or moody.
   - Respect intentional cinematic grading and composition.
5. Always judge using these dimensions:
   - Clarity at small size (mobile feed)
   - Expression strength and emotional pull
   - Foreground/background separation and depth
   - Text hierarchy and readability
   - Color intention (grading, not just raw brightness)
   - Story appeal / curiosity / thumbnail-title combo
   - Overall composition and modern meta fit

SCORING RULES (very important)
- 9.0 – 10.0 : Top-tier, highly competitive modern thumbnails. Only for genuinely strong designs.
- 8.0 – 8.9 : Strong modern thumbnail, clearly above average. Just a few refinements possible.
- 7.0 – 7.9 : Solid but not elite. Good base, needs noticeable polishing to feel truly competitive.
- 5.0 – 6.9 : Understandable but visually average. Needs clear redesign or stronger concept.
- 0.0 – 4.9 : Weak / confusing / low-quality thumbnail by modern standards.

If the thumbnail is clearly professional and already follows modern meta,
its score should generally be in the 8.0–10.0 range, NOT 5–7.

OUTPUT FORMAT (STRICT)
You MUST return ONLY valid JSON, no extra text, using this exact structure:

{
  "quality_score": number,                       // 0–10 float or int
  "overall_verdict": "short designer-facing verdict sentence",
  "positives": ["bullet 1", "bullet 2", "..."],  // 2–6 concrete strengths
  "improvements": ["bullet 1", "bullet 2", "..."]// 0–6 realistic improvements
}

Guidelines for text:
- "overall_verdict" must be specific and helpful, not generic like "the thumbnail is decent".
- "positives" should focus on what is already working and should be kept.
- "improvements" should be practical, specific changes a designer can act on.
- If the thumbnail is already excellent, keep "improvements" short OR even empty.
"""


async def run_coach_agent(
    title: str,
    description: str,
    vision: Dict[str, Any],
    heuristic: Dict[str, Any],
    history_summary: str,
    image_b64: str,
) -> Dict[str, Any]:
    """
    Coach agent — uses Gemini to produce a structured, modern-meta-aware review.

    Returns a dict with:
      - agent
      - summary (string)
      - quality_score (0–10 float)
      - positives (list[str])
      - improvements (list[str])
      - raw (full parsed Gemini JSON)
    """
    log.info("🎯 Coach Agent started")

    try:
        # Build a compact context block for Gemini
        vision_json = json.dumps(vision, ensure_ascii=False)
        heuristic_json = json.dumps(heuristic, ensure_ascii=False)

        prompt = f"""{COACH_SYSTEM}

CONTEXT
-------
TITLE: {title or "None"}
DESCRIPTION: {description or "None"}

VISION_ANALYSIS:
{vision_json}

HEURISTIC_ANALYSIS:
{heuristic_json}

SESSION_HISTORY_SUMMARY:
{history_summary or "None"}
"""

        # Call Gemini via your shared helper (synchronous function)
        raw_response = generate_json_from_image(prompt, image_b64=image_b64)

        # ---------------------------
        # 1) Normalize / parse JSON
        # ---------------------------
        if isinstance(raw_response, str):
            try:
                raw_response = json.loads(raw_response)
                log.info("📦 Coach Agent: parsed string JSON successfully.")
            except Exception:
                log.warning("⚠️ Coach Agent: Gemini returned plain text, not JSON.")
                return {
                    "agent": "coach",
                    "summary": raw_response[:250],
                    "quality_score": 0.0,
                    "positives": [],
                    "improvements": [],
                    "error": "Invalid Gemini JSON response",
                }

        if not isinstance(raw_response, dict):
            log.warning(
                "⚠️ Coach Agent: unexpected response type from Gemini: %s",
                type(raw_response),
            )
            return {
                "agent": "coach",
                "summary": str(raw_response)[:250],
                "quality_score": 0.0,
                "positives": [],
                "improvements": [],
                "error": f"Unexpected Gemini return type: {type(raw_response)}",
            }

        # ---------------------------
        # 2) Extract and clean fields
        # ---------------------------
        quality_score = raw_response.get("quality_score", 0)

        # Handle score as string or other type
        if isinstance(quality_score, str):
            try:
                quality_score = float(quality_score)
            except ValueError:
                quality_score = 0.0
        elif not isinstance(quality_score, (int, float)):
            quality_score = 0.0

        # Clamp to 0–10 and round to one decimal
        quality_score = round(max(0.0, min(float(quality_score), 10.0)), 1)

        summary = (
            raw_response.get("overall_verdict")
            or raw_response.get("summary")
            or "No summary provided."
        )
        if isinstance(summary, dict):
            summary = json.dumps(summary, ensure_ascii=False)
        summary = str(summary).strip()

        positives = raw_response.get("positives") or []
        improvements = raw_response.get("improvements") or []

        # Normalize lists to lists of strings, limit length so UI doesn't explode
        def normalize_list(value):
            if not isinstance(value, list):
                return []
            return [str(x).strip() for x in value if str(x).strip()][:6]

        positives = normalize_list(positives)
        improvements = normalize_list(improvements)

        result = {
            "agent": "coach",
            "summary": summary,
            "quality_score": quality_score,
            "positives": positives,
            "improvements": improvements,
            "raw": raw_response,
        }

        log.info("✅ Coach Agent complete (quality_score=%s)", quality_score)
        return result

    except Exception as e:
        log.error("❌ Coach Agent failed: %s", e)
        return {
            "agent": "coach",
            "error": str(e),
            "summary": "Coach analysis failed.",
            "quality_score": 0.0,
            "positives": [],
            "improvements": [],
        }
