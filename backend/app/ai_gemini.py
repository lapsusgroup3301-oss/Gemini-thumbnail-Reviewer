# backend/app/ai_gemini.py

import os
import google.generativeai as genai
from typing import Optional
import asyncio

# --- Setup Gemini API key ---
api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in environment.")

genai.configure(api_key=api_key)
print("[Gemini] Initialized successfully.")


# --- Async text generation helper ---
async def generate_text(prompt: str, model_name: str = "gemini-2.0-flash", timeout: int = 20) -> str:
    """
    Generate a text response from Gemini asynchronously with timeout safety.
    """
    async def _inner():
        model = genai.GenerativeModel(model_name)
        response = await asyncio.to_thread(model.generate_content, prompt)
        return getattr(response, "text", "").strip() if response else ""

    try:
        return await asyncio.wait_for(_inner(), timeout=timeout)
    except asyncio.TimeoutError:
        return "[Timed out: Gemini API took too long]"
    except Exception as e:
        return f"[Error from Gemini: {e}]"


# --- Helper for structured JSON output (used by agents) ---
async def generate_json_from_text(prompt: str, model_name: str = "gemini-2.0-flash", timeout: int = 25) -> dict:
    """
    Attempts to generate a structured JSON-like response from Gemini.
    """
    text = await generate_text(prompt, model_name=model_name, timeout=timeout)
    import json

    try:
        # Try parsing as JSON directly
        if text.strip().startswith("{"):
            return json.loads(text)
        # Try extracting a JSON block if extra text
        import re
        match = re.search(r"\{.*\}", text, re.S)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    return {"raw_output": text}
