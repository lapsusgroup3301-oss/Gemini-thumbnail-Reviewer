import base64
import io
from PIL import Image

def image_to_base64_png(image: Image.Image) -> str:
    """
    Convert a PIL image to a base64-encoded PNG string.
    Used for sending images (like heatmaps) in JSON responses.
    """
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    img_bytes = buf.getvalue()
    encoded = base64.b64encode(img_bytes).decode("utf-8")
    return encoded
