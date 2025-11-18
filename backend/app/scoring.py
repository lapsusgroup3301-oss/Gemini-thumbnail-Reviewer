# backend/app/scoring.py
"""
Lightweight heuristic scoring for thumbnail images.

Metrics produced (0-10):
- clarity: edge density (proxy for sharpness)
- contrast: histogram dynamic range
- text_readability: uses pytesseract if available, else heuristic on high-contrast text-like regions
- subject_focus: size of largest bright/dark region (proxy for subject)
- emotional_impact: heuristic based on face-detection availability (not included) and color saturation
"""

from PIL import Image, ImageFilter, ImageStat, ImageOps
import numpy as np
import math

# try optional pytesseract (OCR)
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
    # threshold edges to count 'edge' pixels
    edge_pixels = (arr > 30).sum()
    total = arr.size
    return edge_pixels / total  # 0..1

def _contrast_score(img: Image.Image):
    # normalized dynamic range of luminance
    gray = img.convert("L")
    arr = np.array(gray).astype(float)
    # dynamic range: (max - min) / 255
    dyn = (arr.max() - arr.min()) / 255.0
    # also consider stddev
    std = arr.std() / 128.0
    val = 0.6 * dyn + 0.4 * std
    return min(max(val, 0.0), 1.0)

def _text_readability_score(img: Image.Image):
    # If OCR available, check amount of readable text characters detected
    if OCR_AVAILABLE:
        try:
            text = pytesseract.image_to_string(img)
            # crude measure: number of characters and number of lines
            chars = len(text.strip())
            lines = len([l for l in text.splitlines() if l.strip() != ""])
            score = min(1.0, (chars / 100.0) + (lines / 4.0))
            return score
        except Exception:
            pass
    # fallback heuristic: detect strong high-contrast rectangular-ish areas likely to be text
    gray = img.convert("L")
    arr = np.array(gray)
    # compute local contrast via sobel-ish using FIND_EDGES
    edges = gray.filter(ImageFilter.FIND_EDGES)
    earr = np.array(edges)
    # proportion of strong edge pixels in mid-brightness range (text usually has edges)
    strong = ((earr > 50) & (arr > 20) & (arr < 235)).sum()
    total = arr.size
    prop = strong / total
    # scale to 0..1 but small values expected
    score = min(1.0, prop * 10.0)
    return score

def _subject_focus_score(img: Image.Image):
    # heuristic: largest connected bright/dark blob relative to image size via simple thresholding
    gray = img.convert("L")
    arr = np.array(gray)
    # threshold at median
    med = np.median(arr)
    mask = arr < med  # foreground dark region OR bright depending on image; choose dark
    # find approximate bounding box area of mask
    coords = np.argwhere(mask)
    if coords.size == 0:
        return 0.2
    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0)
    bbox_area = (y1 - y0) * (x1 - x0)
    total_area = arr.shape[0] * arr.shape[1]
    frac = bbox_area / total_area
    # subject likely occupies 0.1 .. 0.6 of frame; map to 0..1
    val = min(1.0, max(0.0, (frac - 0.05) * 2.0))
    return val

def _emotional_impact_score(img: Image.Image):
    # proxy: saturation and contrast, and presence of warm tones
    arr = np.array(img).astype(float) / 255.0
    # convert to approx HSV saturation measure
    r, g, b = arr[...,0], arr[...,1], arr[...,2]
    mx = np.maximum(np.maximum(r,g), b)
    mn = np.minimum(np.minimum(r,g), b)
    sat = (mx - mn) / (mx + 1e-6)  # 0..1
    sat_mean = float(np.nanmean(sat))
    # warm tone measure: average (r - b)
    warm = float(np.mean(r - b))
    warm_norm = (warm + 0.5) / 1.0  # not perfect, maps roughly
    val = 0.6 * sat_mean + 0.4 * max(0.0, warm_norm)
    val = min(max(val, 0.0), 1.0)
    return val

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
        "clarity": _normalize_to_0_10(edge_den),           # proxy
        "contrast": _normalize_to_0_10(contrast),
        "text_readability": _normalize_to_0_10(text_read),
        "subject_focus": _normalize_to_0_10(focus),
        "emotional_impact": _normalize_to_0_10(emotional)
    }

    # weighted overall (customize weights as you like)
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

    # short explanations
    explanations = {
        "clarity": f"Edge density suggests clarity score {scores['clarity']}/10.",
        "contrast": f"Contrast heuristics give {scores['contrast']}/10.",
        "text_readability": f"Text readability estimate: {scores['text_readability']}/10.",
        "subject_focus": f"Subject occupies estimated region giving {scores['subject_focus']}/10.",
        "emotional_impact": f"Color/saturation based emotional impact {scores['emotional_impact']}/10."
    }

    # suggestions (simple rule-based)
    suggestions = []
    if scores["text_readability"] < 6.0:
        suggestions.append("Increase headline text size, use bold sans-serif, and ensure high contrast between text and background.")
    if scores["contrast"] < 6.0:
        suggestions.append("Increase contrast or add a vignette behind the subject to separate them from the background.")
    if scores["clarity"] < 5.0:
        suggestions.append("Sharpen the subject or use a tighter crop to make the main subject clearer on small screens.")
    if scores["emotional_impact"] < 5.0:
        suggestions.append("Use higher saturation or a warmer highlight on the subject's face to increase emotional pull.")
    if len(suggestions) == 0:
        suggestions.append("The thumbnail looks solid. Consider A/B testing small variations in text and color to optimize CTR.")

    # generate a simple redesign prompt (string) for future image-gen usage
    prompt = f"High-contrast YouTube thumbnail: close-up of subject, bold large headline text, strong color separation. Style: modern, high click-through."

    # heatmap: simple edge map visualization
    from PIL import ImageOps, ImageEnhance
    edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
    # enhance edges for visualization
    edges = ImageEnhance.Contrast(edges).enhance(2.0)
    edges_rgb = ImageOps.colorize(edges.point(lambda p: p), black="black", white="white")
    # overlay edges onto a transparent-like image for frontend
    heatmap_image = edges_rgb.resize(img.size)

    return {
        "scores": {"overall": overall, **scores},
        "explanations": explanations,
        "suggestions": suggestions,
        "prompts": {"redesign_prompt": prompt},
        "heatmap_image": heatmap_image
    }
