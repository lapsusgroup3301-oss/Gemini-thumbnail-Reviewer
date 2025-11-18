# backend/app/ai_gemini.py
import os
import io
import json
import time
import base64
import hashlib
from typing import Any, Dict, Optional
from PIL import Image



# Optional: reuse utils.image_to_base64_png if you want to return heatmaps from ai_gemini
try:
    from .utils import image_to_base64_png
except Exception:
    image_to_base64_png = None

# try to import official SDK; if not installed, helpful error will surface when used
try:
    import google.generativeai as genai
except Exception:
    genai = None

# configure via env var
API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if genai and API_KEY:
    genai.configure(api_key=API_KEY)

# model to use — pick a vision-capable model available to you (update if needed)
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

# cache directory (simple file cache keyed by image hash)
CACHE_DIR = os.environ.get("THUMBNAIL_CACHE_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "cache"))
os.makedirs(CACHE_DIR, exist_ok=True)


def image_to_b64_jpeg_bytes(img: Image.Image, max_size: int = 1024) -> tuple[str, bytes]:
    """
    Resize (thumbnail) and return base64-encoded JPEG string and raw bytes.
    """
    img2 = img.copy()
    img2.thumbnail((max_size, max_size), Image.LANCZOS)
    buf = io.BytesIO()
    img2.save(buf, format="JPEG", quality=85)
    b = buf.getvalue()
    return base64.b64encode(b).decode("utf-8"), b



def image_hash(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _read_cache(hashkey: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(CACHE_DIR, f"{hashkey}.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _write_cache(hashkey: str, data: Dict[str, Any]):
    path = os.path.join(CACHE_DIR, f"{hashkey}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Try to find a JSON object inside a text blob and parse it.
    """
    import re
    m = re.search(r'(\{.*\})', text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        # fallback: be lenient and try single quotes -> double quotes replacement
        try:
            candidate = m.group(1).replace("'", '"')
            return json.loads(candidate)
        except Exception:
            return None


def call_gemini_image_analysis(pil_img: Image.Image, title: str = "") -> Dict[str, Any]:
    """
    Call Gemini to analyze a thumbnail image and return a parsed result.
    Uses file-cache by image hash. Returns a dictionary that contains at least:
      - id (hash)
      - scores (overall + per-metric)
      - explanations (dict)
      - suggestions (list)
      - prompts (dict)
    If Gemini fails, raises an Exception (caller should catch & fallback).
    """
    # prepare image bytes & hash
    img_b64, img_bytes = image_to_b64_jpeg_bytes(pil_img, max_size=1024)
    h = image_hash(img_bytes)

    # return cached if present
    cached = _read_cache(h)
    if cached:
        cached["_cached"] = True
        return cached

    if genai is None or API_KEY is None:
        raise RuntimeError("google-generativeai SDK not installed or GOOGLE_API_KEY not set in environment.")

    # craft prompt: request compact JSON
    prompt = (
        "You are an expert YouTube thumbnail designer. Analyze the provided image and return COMPACT JSON only with these fields:\n"
        "- ratings: object with numeric 0-10 for clarity, contrast, text_readability, subject_focus, emotional_impact\n"
        "- explanations: one-sentence explanation for each rating\n"
        "- suggestions: array of 3 short, actionable suggestions\n"
        "- redesign_prompt: a single-line prompt suitable for an image-generation model to produce a higher-CTR thumbnail\n"
        f"Context title: {title}\n"
        "Return JSON only, nothing else."
    )

    # Call the SDK. SDK interfaces vary across releases; we attempt a robust call pattern.
    response_text = None
    try:
        # Newer SDKs provide genai.generate(...)
        try:
            gen_resp = genai.generate(
                model=DEFAULT_MODEL,
                input=[{"image": {"image_bytes": img_b64}, "content": prompt}],
                max_output_tokens=512
            )
            # try common fields
            if hasattr(gen_resp, "text"):
                response_text = gen_resp.text
            elif isinstance(gen_resp, (list, tuple)) and len(gen_resp) > 0 and hasattr(gen_resp[0], "text"):
                response_text = gen_resp[0].text
            else:
                response_text = str(gen_resp)
        except Exception:
            # fallback: some SDKs expose genai.models.generate
            try:
                gen_resp = genai.models.generate(model=DEFAULT_MODEL, input=[{"image": {"image_bytes": img_b64}, "content": prompt}], max_output_tokens=512)
                # try to collect textual outputs
                if hasattr(gen_resp, "output") and isinstance(gen_resp.output, (list, tuple)) and len(gen_resp.output) > 0:
                    # join content fields
                    parts = []
                    for o in gen_resp.output:
                        if hasattr(o, "content"):
                            parts.append(getattr(o, "content"))
                        elif isinstance(o, dict) and "content" in o:
                            parts.append(o["content"])
                    response_text = "\n".join(parts)
                else:
                    response_text = str(gen_resp)
            except Exception as e:
                raise

        # try to parse JSON from response_text
        parsed = None
        if response_text:
            parsed = _extract_json_from_text(response_text)

        result = {}
        if parsed:
            # if parsed contains the expected fields, use them
            # But normalize structure to expected schema
            scores = parsed.get("ratings") or parsed.get("scores") or {}
            explanations = parsed.get("explanations") or {}
            suggestions = parsed.get("suggestions") or []
            redesign_prompt = parsed.get("redesign_prompt") or parsed.get("prompt") or parsed.get("redesign") or ""

            result = {
                "id": h,
                "scores": {"overall": None, **scores} if isinstance(scores, dict) else {"overall": None},
                "explanations": explanations if isinstance(explanations, dict) else {"raw": str(explanations)},
                "suggestions": suggestions if isinstance(suggestions, list) else [str(suggestions)],
                "prompts": {"redesign_prompt": redesign_prompt},
                "raw_gemini": parsed,
                "created_at": int(time.time())
            }
        else:
            # No structured JSON found — return raw text for debugging
            result = {
                "id": h,
                "scores": {"overall": None},
                "explanations": {"raw": response_text},
                "suggestions": [],
                "prompts": {"redesign_prompt": ""},
                "raw_gemini": {"text": response_text},
                "created_at": int(time.time())
            }

        # optional: generate small heatmap-like placeholder (if utils available)
        try:
            if image_to_base64_png:
                # create a simple edge-based heatmap for visualization (fast)
                from PIL import ImageFilter, ImageOps, ImageEnhance
                edges = pil_img.convert("L").filter(ImageFilter.FIND_EDGES)
                edges = ImageEnhance.Contrast(edges).enhance(2.0)
                edges_rgb = ImageOps.colorize(edges, black="black", white="white").resize(pil_img.size)
                result["heatmap_base64"] = image_to_base64_png(edges_rgb)
        except Exception:
            pass

        # compute a coarse overall if components exist
        try:
            comp_vals = []
            for k in ("clarity", "contrast", "text_readability", "subject_focus", "emotional_impact"):
                v = result["scores"].get(k)
                if isinstance(v, (int, float)):
                    comp_vals.append(float(v))
                elif isinstance(v, str):
                    try:
                        comp_vals.append(float(v))
                    except Exception:
                        pass
            if comp_vals:
                overall = round(sum(comp_vals) / len(comp_vals), 1)
                result["scores"]["overall"] = overall
            else:
                result["scores"]["overall"] = result["scores"].get("overall") or None
        except Exception:
            pass

        # write cache
        _write_cache(h, result)
        return result

    except Exception as e:
        # bubble up detailed error for caller to log & fallback
        raise RuntimeError(f"Gemini call failed: {e}")
