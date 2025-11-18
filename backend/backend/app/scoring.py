from PIL import Image, ImageFilter, ImageEnhance, ImageOps
import numpy as np
import math

# Optional OCR: will work if pytesseract is installed, otherwise fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

def _to_gray_np(img: Image.Image):
    return np.array(img.convert("L"), dtype=np.uint8)

def _edge_density(img: Image.Image):
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    arr = np.array(edges)
    edge_pixels = (arr > 30).sum()
    total = arr.size
    return edge_pixels / (total + 1e-9)

def _contrast_score(img: Image.Image):
    gray = img.convert("L")
    arr = np.array(gray).astype(float)
    dyn = (arr.max() - arr.min()) / 255.0
    std = arr.std() / 128.0
    val = 0.6 * dyn + 0.4 * std
    return max(0.0, min(1.0, val))

def _text_readability_score(img: Image.Image):
    if OCR_AVAILABLE:
        try:
            text = pytesseract.image_to_string(img)
            chars = len(text.strip())
            lines = len([l for l in text.splitlines() if l.strip() != ""])
            score = min(1.0, (chars / 100.0) + (lines / 4.0))
            return score
        except Exception:
            pass
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    earr = np.array(edges)
    arr = np.array(gray)
    strong = ((earr > 50) & (arr > 20) & (arr < 235)).sum()
    prop = strong / (arr.size + 1e-9)
    return min(1.0, prop * 10.0)

def _subject_focus_score(img: Image.Image):
    gray = img.convert("L")
    arr = np.array(gray)
    med = np.median(arr)
    mask = arr < med
    coords = np.argwhere(mask)
    if coords.size == 0:
        return 0.2
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    bbox_area = max(1, (y1 - y0)) * max(1, (x1 - x0))
    total_area = arr.shape[0] * arr.shape[1]
    frac = bbox_area / (total_area + 1e-9)
    val = min(1.0, max(0.0, (frac - 0.05) * 2.0))
    return val

def _emotional_impact_score(img: Image.Image):
    arr = np.array(img).astype(float) / 255.0
    r, g, b = arr[...,0], arr[...,1], arr[...,2]
    mx = np.maximum(np.maximum(r,g), b)
    mn = np.minimum(np.minimum(r,g), b)
    sat = (mx - mn) / (mx + 1e-6)
    sat_mean = float(np.nanmean(sat))
    warm = float(np.mean(r - b))
    warm_norm = (warm + 0.5) / 1.0
    val = 0.6 * sat_mean + 0.4 * max(0.0, warm_norm)
    return max(0.0, min(1.0, val))

def _normalize_to_0_10(x):
    return round(float(x) * 10.0, 1)

def analyze_image(img: Image.Image, title: str=""):
    # compute heuristics
    edge_den = _edge_density(img)
    contrast = _contrast_score(img)
    text_read = _text_readability_score(img)
    focus = _subject_focus_score(img)
    emotional = _emotional_impact_score(img)

    scores = {
        "clarity": _normalize_to_0_10(edge_den),
        "contrast": _normalize_to_0_10(contrast),
        "text_readability": _normalize_to_0_10(text_read),
        "subject_focus": _normalize_to_0_10(focus),
        "emotional_impact": _normalize_to_0_10(emotional)
    }

    weights = {
        "clarity": 0.18,
        "contrast": 0.18,
        "text_readability": 0.26,
        "subject_focus": 0.22,
        "emotional_impact": 0.16
    }
    overall_value = 0.0
    for k,w in weights.items():
        overall_value += (scores[k] / 10.0) * w
    overall = _normalize_to_0_10(overall_value)

    explanations = {
        "clarity": f"Edge density suggests clarity {scores['clarity']}/10.",
        "contrast": f"Contrast heuristic {scores['contrast']}/10.",
        "text_readability": f"Text readability {scores['text_readability']}/10.",
        "subject_focus": f"Subject focus {scores['subject_focus']}/10.",
        "emotional_impact": f"Emotional impact {scores['emotional_impact']}/10."
    }

    suggestions = []
    if scores["text_readability"] < 6.0:
        suggestions.append("Increase headline text size and use bold sans-serif for readability.")
    if scores["contrast"] < 6.0:
        suggestions.append("Increase contrast or add vignette to separate subject.")
    if scores["clarity"] < 5.0:
        suggestions.append("Sharpen or crop tighter to make the subject clearer.")
    if scores["emotional_impact"] < 5.0:
        suggestions.append("Use warmer highlights and higher saturation for emotional pull.")
    if not suggestions:
        suggestions.append("Thumbnail looks solid; consider small A/B text or color tweaks.")

    prompt = "High-contrast YouTube thumbnail: close-up of subject, bold headline text, strong color separation."

    # create simple heatmap: edge-enhanced visualization
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    edges = ImageEnhance.Contrast(edges).enhance(2.0)
    heatmap_rgb = ImageOps.colorize(edges, black="black", white="white").convert("RGB")
    heatmap_rgb = heatmap_rgb.resize(img.size)

    return {
        "scores": {"overall": overall, **scores},
        "explanations": explanations,
        "suggestions": suggestions,
        "prompts": {"redesign_prompt": prompt},
        "heatmap_image": heatmap_rgb
    }
