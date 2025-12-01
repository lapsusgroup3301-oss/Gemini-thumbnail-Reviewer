# backend/app/agents/heuristic_agent.py

import io
import logging
from typing import Dict, Any

from PIL import Image, ImageStat

log = logging.getLogger("thumbnail-agent")


def _compute_basic_metrics(img: Image.Image) -> Dict[str, float]:
    w, h = img.size
    stat = ImageStat.Stat(img)

    r_mean, g_mean, b_mean = stat.mean
    brightness = (r_mean + g_mean + b_mean) / 3.0
    brightness_score = max(0.0, min(10.0, (brightness / 255.0) * 10.0))

    r_std, g_std, b_std = stat.stddev
    contrast_raw = (r_std + g_std + b_std) / 3.0
    contrast_score = max(0.0, min(10.0, (contrast_raw / 80.0) * 10.0))

    aspect = w / max(h, 1)
    ideal = 16.0 / 9.0
    diff = abs(aspect - ideal)
    if diff < 0.1:
        aspect_score = 9.5
    elif diff < 0.3:
        aspect_score = 8.0
    elif diff < 0.6:
        aspect_score = 6.0
    else:
        aspect_score = max(0.0, 6.0 - (diff - 0.6) * 8.0)

    return {
        "brightness": round(brightness_score, 1),
        "contrast": round(contrast_score, 1),
        "aspect_ratio_fit": round(aspect_score, 1),
        "width": w,
        "height": h,
    }


async def run_heuristic_agent(
    image_bytes: bytes,
    title: str = "",
    description: str = "",
) -> Dict[str, Any]:
    """
    Lightweight, non-Gemini analysis:
    - Brightness, contrast, aspect ratio fit.
    - One heuristic score from these metrics.
    Used for quick metrics and as a sanity check for the coach.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        log.error(f"HeuristicAgent: failed to open image: {e}")
        return {
            "agent": "heuristic",
            "error": str(e),
            "score": 0.0,
            "summary": "Heuristic analysis failed.",
            "details": [],
            "metrics": {},
        }

    metrics = _compute_basic_metrics(img)
    b = metrics["brightness"]
    c = metrics["contrast"]
    a = metrics["aspect_ratio_fit"]

    # simple overall heuristic score
    heuristic_score = round((0.4 * b + 0.4 * c + 0.2 * a) / 1.0, 1)

    details = [
        f"Brightness: {b}/10 (aim for 6–8 for most thumbnails).",
        f"Contrast: {c}/10 (low contrast thumbnails often look flat in the feed).",
        f"Aspect ratio fit: {a}/10 (best around 16:9 for YouTube).",
    ]

    summary = f"Heuristic score {heuristic_score}/10 (brightness, contrast & aspect ratio)."

    return {
        "agent": "heuristic",
        "score": heuristic_score,
        "summary": summary,
        "details": details,
        "metrics": metrics,
    }
