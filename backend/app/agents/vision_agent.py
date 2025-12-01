# backend/app/agents/vision_agent.py

import logging
from typing import Dict, Any
from PIL import Image
import io
import base64
import asyncio
import json

from ..gemini_client import generate_json_from_image

log = logging.getLogger("thumbnail-agent")

VISION_SYSTEM = """
You are a visual analyst for YouTube thumbnails.

Given the thumbnail image, produce a compact description that would help another AI
or creator understand what the viewer actually sees.

Return ONLY valid JSON in this shape:

{
  "summary": "one short sentence describing the scene and main focus",
  "details": [
    "bullet point about subject / faces / character",
    "bullet point about composition / layout",
    "bullet point about colors / lighting",
    "optional extra detail"
  ],
  "tags": ["1–3 short tags like 'horror', 'cinematic', 'cartoonish'"]
}

Focus on what is visually there, not advice or critique.
"""

async def run_vision_agent(image_bytes: bytes) -> Dict[str, Any]:
    """
    Vision agent:
    - Uses PIL to get resolution & aspect ratio.
    - Uses Gemini to describe the visual content.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        aspect_ratio = round(w / max(h, 1), 2)

        # aspect fit score (how close to 16:9)
        target = 16 / 9
        diff = abs(aspect_ratio - target)
        aspect_fit = max(0.0, 10.0 - diff * 10.0)  # simple 0–10 score

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        prompt = f"""{VISION_SYSTEM}

IMAGE_METADATA:
- width: {w}
- height: {h}
- aspect_ratio: {aspect_ratio} (16:9 ≈ 1.78)
"""

        # Run Gemini in worker thread so main loop can time out
        raw = await asyncio.to_thread(
            generate_json_from_image,
            prompt,
            image_b64,
        )

        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                log.warning("Vision Agent got string response that was not valid JSON.")
                raw = {}

        if not isinstance(raw, dict):
            raw = {}

        summary = raw.get("summary") or f"Image size {w}×{h}, aspect ratio {aspect_ratio}."
        details = raw.get("details") or []
        tags = raw.get("tags") or []

        # Ensure details are a list of strings
        if not isinstance(details, list):
            details = [str(details)]
        details = [str(d) for d in details]

        return {
            "agent": "vision",
            "width": w,
            "height": h,
            "aspect_ratio": aspect_ratio,
            "aspect_fit": round(aspect_fit, 1),
            "summary": summary,
            "details": details,
            "tags": tags,
        }

    except Exception as e:
        log.error(f"Vision agent failed: {e}")
        return {
            "agent": "vision",
            "error": str(e),
            "summary": "Vision analysis failed.",
            "details": [],
            "tags": [],
        }
