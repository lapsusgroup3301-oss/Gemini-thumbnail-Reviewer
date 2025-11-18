import io
import time
import uuid
import base64
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
from .scoring import analyze_image
from .utils import image_to_base64_png

# This is the ASGI app uvicorn expects to find
app = FastAPI(title="Thumbnail Reviewer - MVP")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Thumbnail Reviewer backend running"}

@app.post("/api/v1/thumbnail/analyze")
async def analyze_thumbnail(
    file: UploadFile = File(...),
    title: str = Form("")  # optional video title
):
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image uploaded."}, status_code=400)

    analysis = analyze_image(img, title=title)

    result = {
        "id": str(uuid.uuid4()),
        "title": title,
        "scores": analysis["scores"],
        "explanations": analysis["explanations"],
        "suggestions": analysis["suggestions"],
        "prompts": analysis["prompts"],
        "heatmap_base64": image_to_base64_png(analysis["heatmap_image"]),
        "created_at": int(time.time())
    }
    return result
