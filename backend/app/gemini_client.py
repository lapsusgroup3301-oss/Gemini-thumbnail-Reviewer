import os
import re
import json
from typing import Dict, Any
from google import genai

# --- Setup ---
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY environment variable.")

client = genai.Client(api_key=API_KEY)


# --- Helpers ---

def _extract_json(text: str) -> Dict[str, Any]:
    """
    Try to find and parse a JSON block from Gemini text output.
    Returns {} if parsing fails.
    """
    if not text:
        return {}
    match = re.search(r"(\{[\s\S]*\})", text)
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except Exception:
        # As a last resort, try to sanitize bad JSON
        try:
            cleaned = re.sub(r"[^{}:,0-9a-zA-Z\"'\[\]\s]", "", match.group(1))
            return json.loads(cleaned)
        except Exception:
            return {}


# --- Image + prompt Gemini call ---

def generate_json_from_image(prompt: str, image_b64: str) -> Dict[str, Any]:
    """
    Send both text prompt and image to Gemini and return structured JSON.
    Always returns a dict — never a string.
    """
    contents = [
        {"text": prompt},
        {
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_b64,
            }
        },
    ]

    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=contents,
        )

        # Safely extract JSON
        if hasattr(resp, "parsed") and resp.parsed:
            return resp.parsed  # already a dict
        elif hasattr(resp, "text"):
            parsed = _extract_json(resp.text)
            if parsed:
                return parsed
            return {"error": "Gemini returned unstructured text", "raw_text": resp.text}

        return {"error": "Empty Gemini response"}

    except Exception as e:
        return {"error": str(e)}


# --- Text-only Gemini call ---

def generate_json_from_text(prompt: str) -> Dict[str, Any]:
    """
    Send text-only prompt to Gemini and return structured JSON.
    Always returns a dict — never a string.
    """
    try:
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"text": prompt}],
        )

        if hasattr(resp, "parsed") and resp.parsed:
            return resp.parsed
        elif hasattr(resp, "text"):
            parsed = _extract_json(resp.text)
            if parsed:
                return parsed
            return {"error": "Gemini returned plain text", "raw_text": resp.text}

        return {"error": "No response"}

    except Exception as e:
        return {"error": str(e)}
