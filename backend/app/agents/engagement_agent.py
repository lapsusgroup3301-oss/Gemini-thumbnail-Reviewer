# backend/app/agents/engagement_agent.py

import logging
from typing import Dict, Any

log = logging.getLogger("thumbnail-agent")

async def run_engagement_agent(
    vision: Dict[str, Any],
    heuristic: Dict[str, Any],
    coach_summary: str,
) -> Dict[str, Any]:
    """
    Predicts engagement potential based on clarity, quality, and text cues.
    Never returns a string — always a structured dict.
    """
    try:
        heur_score = float(heuristic.get("score", 5))
        clarity = float(vision.get("clarity", vision.get("aspect_ratio", 1.7)))
        coach_text_len = len(coach_summary.strip()) if isinstance(coach_summary, str) else 0

        # Weighted mix
        engagement = (
            (heur_score * 0.4)
            + (min(clarity, 10) * 0.3)
            + (min(coach_text_len / 100, 10) * 0.3)
        )

        engagement_score = round(min(max(engagement, 0), 10), 1)

        return {
            "agent": "engagement",
            "engagement_score": engagement_score,
            "summary": f"Predicted engagement potential: {engagement_score}/10.",
            "factors": {
                "heur_score": heur_score,
                "clarity": clarity,
                "coach_text_len": coach_text_len,
            },
        }

    except Exception as e:
        log.error(f"❌ Engagement Agent failed: {e}")
        return {
            "agent": "engagement",
            "error": str(e),
            "engagement_score": 0.0,
            "summary": "Engagement analysis failed.",
        }
