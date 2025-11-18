# frontend/app.py
import streamlit as st
import requests
from PIL import Image
import io
import base64
import json
import traceback

# Set your backend URL here (must match your running FastAPI)
BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Thumbnail Reviewer (MVP)", layout="centered")
st.title("Thumbnail Reviewer — MVP")

st.markdown(
    "Upload a YouTube thumbnail and get quick AI-like feedback (heuristic MVP)."
)
st.write("If anything goes wrong you'll see an error box below — no blank screen.")

# A small helper to decode base64 images returned by the backend
def b64_to_pil_image(b64str: str) -> Image.Image:
    if b64str.startswith("data:image"):
        # strip data URI prefix if present
        b64str = b64str.split(",", 1)[1]
    img_bytes = base64.b64decode(b64str)
    return Image.open(io.BytesIO(img_bytes)).convert("RGB")

# Wrap whole page in try so errors get shown in UI
try:
    uploaded = st.file_uploader("Upload thumbnail image", type=["png", "jpg", "jpeg"])
    title = st.text_input("Optional video title", "")

    if uploaded is not None:
        # show a small preview
        st.subheader("Preview")
        image = Image.open(uploaded).convert("RGB")
        st.image(image, use_column_width=True)

    if st.button("Analyze"):
        if uploaded is None:
            st.error("Please upload an image first.")
        else:
            # prepare files payload
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {"title": title}
            with st.spinner("Uploading and analyzing..."):
                try:
                    resp = requests.post(
                        f"{BACKEND_URL}/api/v1/thumbnail/analyze",
                        files=files,
                        data=data,
                        timeout=30,
                    )
                    resp.raise_for_status()
                except requests.exceptions.RequestException as e:
                    st.error(f"Request failed: {e}")
                    st.exception(traceback.format_exc())
                else:
                    try:
                        result = resp.json()
                    except Exception as e:
                        st.error("Failed to decode JSON response from backend.")
                        st.code(resp.text[:1000])
                        st.exception(traceback.format_exc())
                        result = None

                    if result is not None:
                        st.success("Analysis complete")
                        scores = result.get("scores", {})
                        st.subheader("Scores")
                        overall = scores.get("overall", "N/A")
                        st.write(f"**Overall:** {overall}/10")

                        # Show metrics
                        metrics = ["clarity", "contrast", "text_readability", "subject_focus", "emotional_impact"]
                        cols = st.columns(len(metrics))
                        for i, key in enumerate(metrics):
                            cols[i].metric(label=key.replace("_", " ").title(), value=f"{scores.get(key, 'N/A')}/10")

                        st.subheader("Suggestions")
                        for s in result.get("suggestions", []):
                            st.write("- " + s)

                        st.subheader("Explanations")
                        for k, v in result.get("explanations", {}).items():
                            st.write(f"**{k.replace('_',' ').title()}** — {v}")

                        st.subheader("Redesign prompt")
                        prompt = result.get("prompts", {}).get("redesign_prompt", "")
                        if prompt:
                            st.code(prompt)

                        # Show heatmap if available
                        heatmap_b64 = result.get("heatmap_base64")
                        if heatmap_b64:
                            st.subheader("Heatmap")
                            try:
                                hm = b64_to_pil_image(heatmap_b64)
                                st.image(hm, use_column_width=True)
                            except Exception:
                                # sometimes backend returns shortened or different format
                                st.write("Heatmap returned but failed to render.")
                                st.text(heatmap_b64[:400])

except Exception as e_outer:
    st.error("An unexpected error occurred while rendering the app.")
    st.exception(traceback.format_exc())

st.markdown("---")
st.caption("If the page stays blank after this, open the browser console (F12 → Console) and paste any red errors here.")
