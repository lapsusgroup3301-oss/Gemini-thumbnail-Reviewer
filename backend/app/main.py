# backend/app/main.py
import io
import uuid
import time
import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image

# local modules
from .scoring import analyze_image as heuristic_analyze_image
from .utils import image_to_base64_png

# Try to import the Gemini module (may raise if not installed)
try:
    from .ai_gemini import call_gemini_image_analysis, image_hash
except Exception:
    call_gemini_image_analysis = None
    image_hash = None

app = FastAPI(title="Thumbnail Reviewer | MVP")

# CORS -- if needed, configure in real deploy
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to specific origin in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/thumbnail/analyze")
async def analyze_thumbnail(file: UploadFile = File(...), title: str = Form("")):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image uploaded."}, status_code=400)

    # Compute a hash (for logging or caching)
    try:
        from .ai_gemini import image_hash as _image_hash_fn
        _, jpeg_bytes = (lambda p: (None, p))(None)  # placeholder
    except Exception:
        _image_hash_fn = None

    # First: try Gemini if available
    if call_gemini_image_analysis is not None:
        try:
            gemini_result = call_gemini_image_analysis(img, title=title)
            # Normalize the response to the standard schema expected by frontend
            # If gemini_result already looks like the correct schema, reuse; else map
            result = {
                "id": gemini_result.get("id", str(uuid.uuid4())),
                "title": title,
                "scores": gemini_result.get("scores", {"overall": None}),
                "explanations": gemini_result.get("explanations", {}),
                "suggestions": gemini_result.get("suggestions", []),
                "prompts": gemini_result.get("prompts", {}),
                "heatmap_base64": gemini_result.get("heatmap_base64"),
                "created_at": gemini_result.get("created_at", int(time.time())),
                "raw_gemini": gemini_result.get("raw_gemini"),
            }
            # If Gemini returned no useful scores, fallback to heuristics for numeric scoring
            scores = result["scores"]
            if not scores or (isinstance(scores, dict) and scores.get("overall") in (None, "", 0)):
                # run heuristics to compute numeric values
                h_analysis = heuristic_analyze_image(img, title=title)
                # merge: keep suggestions/explanations from Gemini (text), numeric from heuristics
                result["scores"] = h_analysis.get("scores", {"overall": None})
                # keep Gemini suggestions if present; else use heuristics suggestions
                if not result.get("suggestions"):
                    result["suggestions"] = h_analysis.get("suggestions", [])
                # keep heatmap if not present
                if not result.get("heatmap_base64"):
                    result["heatmap_base64"] = image_to_base64_png(h_analysis.get("heatmap_image")) if h_analysis.get("heatmap_image") and image_to_base64_png else None

            return result

        except Exception as e:
            # log error server-side (print for now)
            print("Gemini integration failed, falling back to heuristics. Error:", e)

    # If Gemini not available or failed, run heuristics
    analysis = heuristic_analyze_image(img, title=title)
    result = {
        "id": str(uuid.uuid4()),
        "title": title,
        "scores": analysis.get("scores", {}),
        "explanations": analysis.get("explanations", {}),
        "suggestions": analysis.get("suggestions", []),
        "prompts": analysis.get("prompts", {}),
        "heatmap_base64": image_to_base64_png(analysis.get("heatmap_image")) if analysis.get("heatmap_image") and image_to_base64_png else None,
        "created_at": int(time.time())
    }
    return result
