# backend/app/utils.py
import io
import base64
from PIL import Image

def image_to_base64_png(img):
    """
    Returns a base64-encoded PNG (string) for easy embedding in frontend.
    """
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_bytes = buffered.getvalue()
    b64 = base64.b64encode(img_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"
