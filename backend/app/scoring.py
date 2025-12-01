# backend/app/scoring.py

import io
import os
from typing import Any, Dict, List, Tuple

from PIL import Image, ImageStat

# Gemini integration (same import as your project)
try:
    from .ai_gemini import call_gemini_image_analysis
except Exception:
    call_gemini_image_analysis = None  # type: ignore

# Only call Gemini if this flag is set AND ai_gemini imported
USE_GEMINI = os.environ.get("USE_GEMINI_THUMB", "0") == "1"


# ---------- Image + heuristics (UI only) ----------

def _open_image(image_bytes: bytes) -> Image.Image:
    """Decode raw bytes into a PIL Image."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        return img
    except Exception as e:
        raise ValueError(f"Could not decode image: {e}")


def _basic_heuristics(img: Image.Image) -> Dict[str, float]:
    """
    Simple brightness / contrast / aspect info for the UI.

    IMPORTANT: these values are NOT used for scoring or review,
    only for quick visual metrics.
    """
    w, h = img.size
    stat = ImageStat.Stat(img)

    # brightness 0–255 -> 0–10
    r_mean, g_mean, b_mean = stat.mean
    brightness = (r_mean + g_mean + b_mean) / 3.0
    brightness_score = max(0.0, min(10.0, (brightness / 255.0) * 10.0))

    # contrast: stddev -> rough 0–10 scaling
    r_std, g_std, b_std = stat.stddev
    contrast_raw = (r_std + g_std + b_std) / 3.0
    contrast_score = max(0.0, min(10.0, (contrast_raw / 80.0) * 10.0))

    aspect = w / max(h, 1)
    ideal_aspect = 16.0 / 9.0
    ratio_delta = abs(aspect - ideal_aspect)

    if ratio_delta < 0.1:
        aspect_score = 9.5
    elif ratio_delta < 0.3:
        aspect_score = 8.0
    elif ratio_delta < 0.6:
        aspect_score = 6.0
    else:
        aspect_score = max(0.0, 6.0 - (ratio_delta - 0.6) * 8.0)

    return {
        "brightness": round(brightness_score, 1),
        "contrast": round(contrast_score, 1),
        "aspect_ratio": round(aspect_score, 1),
        "width": w,
        "height": h,
    }


# ---------- Gemini helpers ----------

def _safe_float(v: Any, default: float = 5.5) -> float:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except Exception:
            return default
    return default


def _extract_gemini_scores(gemini: Dict[str, Any]) -> Dict[str, float]:
    """
    Normalize Gemini output into 0–10 scores for:
    clarity, contrast, text_readability, subject_focus, emotional_impact.

    Works with either:
      - gemini["scores"][...]  or
      - gemini["raw_gemini"]["ratings"][...]
    """
    base = gemini.get("scores") or {}
    ratings = gemini.get("raw_gemini", {}).get("ratings") or {}

    def g(key: str, default: float = 5.5) -> float:
        return _safe_float(
            base.get(key)
            or ratings.get(key)
            or base.get(key.replace("_", " "))
            or ratings.get(key.replace("_", " ")),
            default,
        )

    def clamp10(x: float) -> float:
        return max(0.0, min(10.0, x))

    return {
        "clarity": clamp10(g("clarity")),
        "contrast": clamp10(g("contrast")),
        "text_readability": clamp10(g("text_readability")),
        "subject_focus": clamp10(g("subject_focus")),
        "emotional_impact": clamp10(g("emotional_impact")),
    }


def _build_aspects_from_gemini(gem_scores: Dict[str, float]) -> Dict[str, float]:
    """
    Build 5 aspects (0–10 each) derived ONLY from Gemini scores.
    """
    cl = gem_scores["clarity"]
    co = gem_scores["contrast"]
    tr = gem_scores["text_readability"]
    sf = gem_scores["subject_focus"]
    em = gem_scores["emotional_impact"]

    def clamp10(x: float) -> float:
        return round(max(0.0, min(10.0, x)), 1)

    visual_clarity = 0.5 * cl + 0.2 * co + 0.3 * sf
    text_effectiveness = tr
    subject_focus = sf
    emotional_pull = em
    technical_balance = 0.4 * cl + 0.3 * co + 0.3 * tr

    return {
        "visual_clarity": clamp10(visual_clarity),
        "text_effectiveness": clamp10(text_effectiveness),
        "subject_focus": clamp10(subject_focus),
        "emotional_pull": clamp10(emotional_pull),
        "technical_balance": clamp10(technical_balance),
    }


# ---------- Scoring: Gemini-only with calibration ----------

def _compute_final_score(
    gem_scores: Dict[str, float],
    aspects: Dict[str, float],
) -> float:
    """
    Final score is Gemini-only, calibrated for YouTube thumbnails.

    Rough mapping after calibration:
      - bad:    3–5
      - avg:    5–6.8
      - good:   6.8–7.9
      - strong: 7.9–9.5
    """
    cl = gem_scores["clarity"]
    tr = gem_scores["text_readability"]
    sf = gem_scores["subject_focus"]
    em = gem_scores["emotional_impact"]
    co = gem_scores["contrast"]

    # Base weighted Gemini score (still on 0–10 scale)
    gem_raw = (
        0.22 * cl +
        0.24 * tr +
        0.24 * sf +
        0.18 * em +
        0.12 * co
    )

    # Aspect structure
    vals = list(aspects.values())
    high_count = sum(v >= 8.0 for v in vals)
    mid_count = sum(6.0 <= v < 8.0 for v in vals)
    low_soft = sum(v < 6.0 for v in vals)
    low_hard = sum(v < 5.0 for v in vals)

    score = gem_raw

    # --- boosts for genuinely strong thumbs ---
    if high_count >= 3 and low_hard <= 1:
        score = max(score, 7.8)  # at least "strong"
    if high_count >= 4 and low_hard == 0:
        score = max(score, 8.4)  # push into high tier

    # --- caps for weak thumbs ---
    if low_hard >= 3:
        score = min(score, 6.2)  # can't pretend to be "good"
    elif low_soft >= 3 and high_count == 0:
        score = min(score, 6.8)

    # --- global calibration ---
    # shift + stretch:  score_cal = 1.1 * score + 1.0
    score = 1.1 * score + 1.0

    # clamp to [0, 10]
    score = max(0.0, min(10.0, score))

    return round(score, 1)


# ---------- Review generation ----------

def _build_review_lines(
    final_overall: float,
    aspects: Dict[str, float],
    gemini: Dict[str, Any] | None,
) -> List[str]:
    """
    Short, useful review.

    Priority:
      1. Use Gemini-provided text if available.
      2. Otherwise, derive from aspects.
    """
    lines: List[str] = []

    vc = aspects["visual_clarity"]
    te = aspects["text_effectiveness"]
    sf = aspects["subject_focus"]
    em = aspects["emotional_pull"]
    tb = aspects["technical_balance"]

    score_str = f"{final_overall:.1f}/10"

    # ---------- 1) Summary ----------
    used_gem_summary = False
    if gemini:
        summary = gemini.get("summary") or gemini.get("overall_comment")
        if isinstance(summary, str) and len(summary.strip()) > 10:
            lines.append(f"{summary.strip()} ({score_str}).")
            used_gem_summary = True

    if not used_gem_summary:
        if final_overall >= 8.7:
            lines.append(f"Top-tier thumbnail ({score_str}); it should perform very well.")
        elif final_overall >= 7.5:
            lines.append(f"Strong thumbnail ({score_str}); only small tweaks are likely to help.")
        elif final_overall >= 6.5:
            lines.append(f"Decent thumbnail ({score_str}); the idea works but clarity/readability can be sharper.")
        elif final_overall >= 5.0:
            lines.append(f"Below-average thumbnail ({score_str}); it will struggle to stand out in the feed.")
        else:
            lines.append(f"Weak thumbnail ({score_str}); it’s hard to read or understand quickly.")

    # ---------- 2) What’s working ----------
    positives: List[str] = []

    if gemini:
        strengths = gemini.get("strengths") or gemini.get("positives") or []
        for s in strengths:
            if isinstance(s, str) and len(s.strip()) > 5:
                positives.append(s.strip())

    if not positives:
        if vc >= 7.0:
            positives.append("The main subject and idea read clearly at a quick glance.")
        if te >= 7.0:
            positives.append("The text is readable and supports the video idea.")
        if sf >= 7.0:
            positives.append("The main subject stands out from the background.")
        if em >= 7.0:
            positives.append("The emotion or mood is strong enough to grab attention.")
        if tb >= 7.0:
            positives.append("Composition and technical quality look solid overall.")

    if not positives:
        positives.append("The core concept of the thumbnail is understandable.")

    lines.append("What’s working:")
    for p in positives[:3]:
        lines.append(f"- {p}")

    # ---------- 3) What you could test next ----------
    suggestions: List[str] = []

    if gemini:
        raw_sugs = (
            gemini.get("suggestions")
            or gemini.get("improvements")
            or gemini.get("weaknesses")
            or []
        )
        for s in raw_sugs:
            if isinstance(s, str):
                s = s.strip()
                if len(s) > 5:
                    suggestions.append(s)

    if len(suggestions) < 2:
        if vc < 6.0:
            suggestions.append(
                "Make the main subject and message clearer so it reads instantly on a phone screen."
            )
        if te < 6.0:
            suggestions.append(
                "Use fewer words with larger, bolder text to improve readability in the YouTube feed."
            )
        if sf < 6.0:
            suggestions.append(
                "Make the key subject bigger or separate it more from the background."
            )
        if em < 6.0:
            suggestions.append(
                "Push the emotion or tension a bit further so it feels more clickable."
            )
        if tb < 6.0:
            suggestions.append(
                "Clean up the composition or adjust contrast so the image feels less busy."
            )

    if suggestions:
        lines.append("What you could test next:")
        for s in suggestions[:4]:
            lines.append(f"- {s}")

    return lines


# ---------- Public API ----------

def rate_thumbnail(
    image_bytes: bytes,
    title: str = "",
    description: str = "",
) -> Tuple[float, List[str], Dict[str, Any]]:
    """
    Main scoring function used by the FastAPI endpoint.

    Returns:
        - score: float (0–10)
        - review_lines: list[str]
        - extra_meta: dict (for UI / debugging)
    """
    img = _open_image(image_bytes)
    heuristics = _basic_heuristics(img)

    gemini_result: Dict[str, Any] | None = None
    gemini_used = False
    gem_scores: Dict[str, float] | None = None

    if USE_GEMINI and call_gemini_image_analysis is not None:
        try:
            # IMPORTANT: keep this signature compatible with your ai_gemini.py
            gemini_result = call_gemini_image_analysis(img, title=title)
            gem_scores = _extract_gemini_scores(gemini_result or {})
            gemini_used = True
        except Exception as e:
            print("Gemini error in rate_thumbnail:", e)
            gemini_result = {"error": str(e)}
            gemini_used = False

    # Fallback so the app doesn’t crash if Gemini fails
    if gem_scores is None:
        gem_scores = {
            "clarity": 5.5,
            "contrast": 5.5,
            "text_readability": 5.5,
            "subject_focus": 5.5,
            "emotional_impact": 5.5,
        }

    aspects = _build_aspects_from_gemini(gem_scores)
    final_score = _compute_final_score(gem_scores, aspects)

    review_lines = _build_review_lines(
        final_score,
        aspects,
        gemini_result if gemini_used else None,
    )

    extra_meta: Dict[str, Any] = {
        "heuristics": heuristics,
        "gemini_used": gemini_used,
        "use_gemini_flag": USE_GEMINI,
        "gemini_scores": gem_scores,
        "aspects": aspects,
    }

    if gemini_result:
        extra_meta["gemini"] = {
            "id": gemini_result.get("id"),
            "scores": gemini_result.get("scores"),
            "prompts": gemini_result.get("prompts"),
            "cached": bool(gemini_result.get("_cached")),
            "error": gemini_result.get("error"),
        }

    return final_score, review_lines, extra_meta
