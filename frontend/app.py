import requests
import os
import re
from pathlib import Path
import streamlit as st
import runpy
import streamlit as st

API_BASE = "http://127.0.0.1:8000"
API_ANALYZE = f"{API_BASE}/api/v1/thumbnail/analyze"

PAGE_TITLE = "Thumbnail Reviewer · Gemini Agent"

# paths
HERE = Path(__file__).resolve().parent
ENV_PATH = HERE.parent / ".env"
PROJECT_ROOT = HERE.parent
ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"


GEMINI_KEY_NAME = "GEMINI_API_KEY"
PLACEHOLDER_VALUES = {"", "your_key_here", "YOUR_KEY_HERE", "your_key", "replace_me"}

def read_text(path: Path):
    try:
        return path.read_text(encoding="utf-8")
    except:
        return None

def write_text(path: Path, txt: str):
    path.write_text(txt, encoding="utf-8")

def extract_key(contents: str | None):
    if not contents:
        return None
    for line in contents.splitlines():
        line = line.strip()
        if line.startswith(f"{GEMINI_KEY_NAME}="):
            return line.split("=", 1)[1].strip()
    return None

def save_env_from_example(user_key: str):
    if not ENV_EXAMPLE_PATH.exists():
        raise FileNotFoundError(".env.example is missing")

    example_text = read_text(ENV_EXAMPLE_PATH)
    if example_text is None:
        raise RuntimeError(".env.example unreadable")

    # remove old .env if present
    if ENV_PATH.exists():
        try:
            ENV_PATH.unlink()
        except Exception:
            # ignore unlink errors and try to overwrite by write_text
            pass

    pattern = re.compile(rf"^{GEMINI_KEY_NAME}\s*=.*$", flags=re.MULTILINE)
    new_line = f"{GEMINI_KEY_NAME}={user_key}"

    if pattern.search(example_text):
        new_contents = pattern.sub(new_line, example_text)
    else:
        new_contents = example_text + ("\n" if not example_text.endswith("\n") else "") + new_line + "\n"

    write_text(ENV_PATH, new_contents)

# ---------- startup check ----------
env_contents = read_text(ENV_PATH)
current_key = extract_key(env_contents)
needs_key = current_key is None or current_key in PLACEHOLDER_VALUES

if needs_key:
    # Set a minimal page config so modal-looking UI centers nicely
    try:
        st.set_page_config(page_title="API Key Required", layout="centered")
    except Exception:
        # older streamlit may throw if page_config already set; ignore
        pass

    # Simple, clear blocking UI (works for all Streamlit versions)
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h2 style='text-align:center;'>Gemini API Key required</h2>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="max-width:820px;margin-left:auto;margin-right:auto;">
        <p>
        The app needs a valid <code>GEMINI_API_KEY</code> in <code>.env</code>.
        You can paste your key below. The script will create/overwrite <code>.env</code>
        from <code>.env.example</code>, preserving all other variables and replacing only
        the <code>GEMINI_API_KEY</code> value.
        </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
    "<p style='text-align:center;color:gray;'>Your API key is stored locally in the .env file and never sent to any external server.</p>",
    unsafe_allow_html=True
    )

    key_input = st.text_input("Enter your Gemini API Key", type="password", key="gemini_input")

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        if st.button("Save & Continue"):
            if not key_input or not key_input.strip():
                st.error("API key cannot be empty.")
            else:
                try:
                    save_env_from_example(key_input.strip())
                    st.success("Saved! The app will reload now.")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to save key: {e}")
    with c2:
        if st.button("I already have .env (re-check)"):
            # re-check .env in case user created it externally
            env_contents = read_text(ENV_PATH)
            current_key = extract_key(env_contents)
            if current_key and current_key not in PLACEHOLDER_VALUES:
                os.environ[GEMINI_KEY_NAME] = current_key
                st.success("Found valid key in .env. Reloading app.")
                st.experimental_rerun()
            else:
                st.warning("No valid key detected in .env. Please paste your key or follow README.")
    with c3:
        if st.button("Cancel"):
            st.info("The app is blocked until a valid GEMINI_API_KEY is provided.")

    # Block the rest of the app until key is set.
    st.stop()

# If key exists, load into environment for downstream code
existing_key = extract_key(read_text(ENV_PATH))
if existing_key:
    os.environ[GEMINI_KEY_NAME] = existing_key

st.set_page_config(
    page_title=PAGE_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- STYLING ----------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {
        font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, #1f2937 0, transparent 55%),
            radial-gradient(circle at bottom right, #020617 0, transparent 60%),
            #020617;
        color: #e5e7eb;
    }

    [data-testid="stSidebar"] {
        background: #020617;
    }

    .app-shell {
        padding: 1.8rem 2.1rem 2.4rem;
        max-width: 1240px;
        margin: 0 auto;
    }

    .section-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        color: #6b7280;
        margin-bottom: 0.55rem;
        letter-spacing: 0.12em;
    }

    .card {
        background: rgba(15,23,42,0.96);
        border-radius: 1.15rem;
        padding: 1.2rem 1.25rem 1.3rem;
        border: 1px solid rgba(148,163,184,0.25);
        box-shadow: 0 18px 40px rgba(0,0,0,0.45);
        backdrop-filter: blur(16px);
        animation: floatIn 0.45s ease-out;
    }

    .card-soft {
        background: rgba(15,23,42,0.9);
        border-radius: 0.9rem;
        padding: 0.75rem 0.9rem;
        border: 1px solid rgba(148,163,184,0.2);
    }

    .pill {
        font-size: 0.7rem;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        background: rgba(15,23,42,0.95);
        border: 1px solid rgba(148,163,184,0.4);
        color: #9ca3af;
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
    }

    .pill-dot {
        width: 0.38rem;
        height: 0.38rem;
        border-radius: 999px;
        background: #22c55e;
        display: inline-block;
    }

    .score-badge {
        display: inline-flex;
        align-items: baseline;
        gap: 0.2rem;
        padding: 0.20rem 0.9rem 0.22rem 0.8rem;
        background: linear-gradient(135deg, #22c55e, #4ade80);
        border-radius: 999px;
        color: #022c22;
        box-shadow: 0 14px 30px rgba(34,197,94,0.35);
        transform-origin: left center;
        animation: scorePop 0.45s ease-out;
    }

    .score-badge .value {
        font-size: 1.6rem;
        font-weight: 700;
    }

    .score-badge .unit {
        font-size: 0.8rem;
        font-weight: 600;
        opacity: 0.85;
    }

    .review-heading {
        font-size: 0.9rem;
        font-weight: 600;
        margin: 1rem 0 0.45rem;
    }

    .review-item {
        font-size: 0.82rem;
        color: #d1d5db;
        padding: 0.35rem 0.5rem;
        border-radius: 0.7rem;
        background: linear-gradient(90deg, rgba(15,23,42,0.9), rgba(15,23,42,0.4));
        border: 1px solid rgba(31,41,55,0.75);
        margin-bottom: 0.28rem;
    }

    .review-item .index {
        opacity: 0.7;
        margin-right: 0.25rem;
    }

    .powered-note {
        font-size: 0.75rem;
        color: #6b7280;
        margin-top: 0.6rem;
    }

    /* Button styling */
    div.stButton > button {
        border-radius: 999px;
        padding: 0.4rem 1.4rem;
        border: 1px solid rgba(56,189,248,0.6);
        background: radial-gradient(circle at top left, #38bdf8, #0ea5e9);
        color: #0b1220;
        font-weight: 600;
        font-size: 0.86rem;
        box-shadow: 0 14px 30px rgba(8,47,73,0.7);
        transition: transform 0.12s ease-out, box-shadow 0.12s ease-out, filter 0.12s ease-out;
    }

    div.stButton > button:hover {
        transform: translateY(-1px) scale(1.01);
        box-shadow: 0 18px 40px rgba(8,47,73,0.9);
        filter: brightness(1.05);
    }

    div.stButton > button:active {
        transform: translateY(0) scale(0.99);
        box-shadow: 0 10px 22px rgba(8,47,73,0.7);
    }

    /* Alert (success / error) */
    [data-testid="stAlert"] {
        border-radius: 0.9rem;
        border-width: 1px;
    }

    /* Expander tweaks */
    [data-testid="stExpander"] {
        border-radius: 0.9rem;
        border: 1px solid rgba(55,65,81,0.9);
        background: rgba(15,23,42,0.92);
    }

    [data-testid="stExpander"] > details > summary {
        padding-top: 0.5rem;
        padding-bottom: 0.5rem;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea textarea {
        border-radius: 0.6rem;
        border: 1px solid rgba(55,65,81,0.9);
        background: rgba(15,23,42,0.9);
        color: #e5e7eb;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: rgba(56,189,248,0.9);
        box-shadow: 0 0 0 1px rgba(56,189,248,0.6);
    }

    /* Radio spacing */
    div[role="radiogroup"] > label {
        padding: 0.12rem 0;
        font-size: 0.82rem;
    }

    /* Keyframes */
    @keyframes floatIn {
        from {
            transform: translateY(8px) scale(0.98);
            opacity: 0;
        }
        to {
            transform: translateY(0) scale(1);
            opacity: 1;
        }
    }

    @keyframes scorePop {
        0% {
            transform: scale(0.7);
            opacity: 0;
        }
        60% {
            transform: scale(1.05);
            opacity: 1;
        }
        100% {
            transform: scale(1.0);
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-shell">', unsafe_allow_html=True)

# ---------- STATE ----------
if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "session_id" not in st.session_state:
    st.session_state.session_id = ""

if "last_mode_label" not in st.session_state:
    st.session_state.last_mode_label = "Quick analysis"

# ---------- HEADER ----------
header_left, header_right = st.columns([0.7, 0.3])
with header_left:
    st.markdown(
        """
        <div style="display:flex;flex-direction:column;gap:0.25rem;">
            <div style="display:flex;align-items:center;gap:0.5rem;">
                <h2 style="margin-bottom:0rem;">Thumbnail Reviewer AI</h2>
                <span class="pill">
                    <span class="pill-dot"></span>
                    Gemini multi-agent
                </span>
            </div>
            <p style="font-size:0.82rem;color:#9ca3af;margin-bottom:0.1rem;">
                Upload a YouTube thumbnail and get a scored review, heuristic breakdown, and a coach that speaks like a creator.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with header_right:
    st.markdown(
        """
        <div style="text-align:right;font-size:0.75rem;color:#6b7280;margin-top:0.3rem;">
            Concierge track · Creator tooling<br/>
            <span style="color:#9ca3af;">Session-aware, powered by Gemini</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)

left, right = st.columns([1.05, 0.95])

# =========================================================
# LEFT: INPUT + ANALYZE
# =========================================================
with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Thumbnail input</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drag and drop file here",
        type=["png", "jpg", "jpeg", "webp"],
        label_visibility="collapsed",
    )

    if uploaded:
        st.image(uploaded, caption="Preview", use_container_width=True)

    title_input = st.text_input("Video title (optional)")
    desc_input = st.text_area("Description (optional)", height=80)

    st.markdown("<hr style='opacity:0.22;margin:0.9rem 0;'>", unsafe_allow_html=True)

    mode_label = st.radio(
        "Analysis mode",
        ["Quick analysis", "Deep analysis (more Gemini reasoning)"],
        index=0,
        help="Quick: fastest, good baseline. Deep: Gemini spends more time and can be slower, but can give richer feedback.",
    )
    mode_key = "deep" if mode_label.startswith("Deep") else "quick"

    st.caption(
        "Quick is usually enough. Use Deep when you want Gemini to think harder about composition, story and redesign ideas."
    )

    st.write("")
    analyze_clicked = st.button("Analyze thumbnail")

    if analyze_clicked:
        if uploaded is None:
            st.warning("Upload a thumbnail first.")
        else:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            data = {
                "title": title_input,
                "description": desc_input,
                "session_id": st.session_state.session_id,
                "mode": mode_key,
            }
            timeout = 60 if mode_key == "quick" else 120

            try:
                with st.spinner("Running multi-agent analysis with Gemini…"):
                    r = requests.post(API_ANALYZE, files=files, data=data, timeout=timeout)
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach backend: {e}")
            else:
                if not r.ok:
                    st.error(r.text)
                else:
                    result = r.json()
                    st.session_state.last_result = result
                    st.session_state.session_id = result.get("session_id", "")
                    st.session_state.last_mode_label = mode_label
                    st.success("Analysis complete.")

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# RIGHT: RESULTS
# =========================================================
with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-label">Result</div>', unsafe_allow_html=True)

    result = st.session_state.last_result
    if not result:
        st.markdown(
            """
            <div style="color:#6b7280;font-size:0.8rem;padding:0.4rem 0.2rem;">
                No analysis yet. Upload a thumbnail on the left and click <strong>Analyze thumbnail</strong>. 
                We’ll score it and then break down what the Vision, Heuristic and Coach agents see.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop()

    score = result.get("score")
    review = result.get("review", [])
    meta = result.get("meta") or {
        "heuristics": {},
        "agents": result.get("agents", {}),
        "gemini_used": True,
    }

    col1, col2 = st.columns([0.55, 0.45])
    with col1:
        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;gap:0.3rem;">
                <div class="score-badge">
                    <span class="value">{score}</span>
                    <span class="unit">/10</span>
                </div>
                <div style="font-size:0.8rem;color:#9ca3af;margin-top:0.15rem;">
                    Generated using Vision + Heuristic + Coach agents.
                </div>
                <div style="font-size:0.75rem;color:#6b7280;">
                    Mode: <span style="color:#e5e7eb;">{st.session_state.last_mode_label}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        heur = meta.get("heuristics", {})
        st.markdown('<div class="card-soft">', unsafe_allow_html=True)
        st.markdown(
            '<div style="font-weight:600;margin-bottom:0.4rem;font-size:0.82rem;">Quick metrics</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f"• Brightness: **{heur.get('brightness', '?')}/10**")
        st.markdown(f"• Contrast: **{heur.get('contrast', '?')}/10**")
        st.markdown(f"• Aspect fit: **{heur.get('aspect_ratio_fit', '?')}/10**")
        if meta.get("gemini_used"):
            st.markdown(
                "<div style='margin-top:0.45rem;'><span class='pill'><span class='pill-dot'></span>Gemini pipeline used</span></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="review-heading">Review</div>', unsafe_allow_html=True)
    if review:
        for i, line in enumerate(review, start=1):
            st.markdown(
                f"<div class='review-item'><span class='index'>{i}.</span>{line}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No consolidated review text returned from the agents.")

    st.markdown('<hr style="opacity:0.25;margin:1rem 0 0.9rem 0;">', unsafe_allow_html=True)
    st.markdown('<div class="review-heading">Agent breakdown</div>', unsafe_allow_html=True)

    agents = meta.get("agents") or result.get("agents", {})

    # Vision Agent
    with st.expander("Vision Agent"):
        v = agents.get("vision", {})
        st.write("**Summary:**", v.get("summary", ""))
        details = v.get("details") or []
        if details:
            st.write("**Visual notes:**")
            for d in details:
                st.write("- " + str(d))

    # Heuristic Agent
    with st.expander("Heuristic Agent"):
        h = agents.get("heuristic", {})
        st.write("**Summary:**", h.get("summary", ""))
        metrics = h.get("metrics") or {}
        if metrics:
            st.write("**Raw metrics:**")
            st.write(
                f"- Brightness: {metrics.get('brightness')}, "
                f"Contrast: {metrics.get('contrast')}, "
                f"Aspect fit: {metrics.get('aspect_ratio_fit')}"
            )
        details = h.get("details") or []
        for d in details:
            st.write("- " + str(d))

    # Coach Agent
    with st.expander("Coach Agent", expanded=True):
        c = agents.get("coach", {})
        st.write("**Summary:**", c.get("summary", ""))

        strengths = c.get("positives") or []
        fixes = c.get("improvements") or []
        micro = c.get("micro_tweaks") or []
        redesign = c.get("redesign_ideas") or []

        quality_raw = c.get("quality_score") or 0.0
        try:
            quality = float(quality_raw)
        except (TypeError, ValueError):
            quality = 0.0

        if strengths:
            st.write("**What’s already working:**")
            for s in strengths[:4]:
                st.write("- " + str(s))

        if quality >= 8.3:
            st.info(
                "This thumbnail already looks strong for the current meta. "
                "If you want micro-tweaks to squeeze a bit more performance, you can reveal them below."
            )
            show_micro = st.button("Show micro-tweaks", key="show_micro_tweaks")
            if show_micro and micro:
                st.write("**Micro-tweaks to test:**")
                for m in micro[:6]:
                    st.write("- " + str(m))
        else:
            if fixes:
                st.write("**Fix these first:**")
                for f in fixes[:5]:
                    st.write("- " + str(f))

            if redesign:
                st.write("**Redesign directions to experiment with:**")
                for r_idea in redesign[:4]:
                    st.write("- " + str(r_idea))


    st.markdown(
        "<div class='powered-note'>Session memory: this agent remembers your recent thumbnails and uses them for context.</div>",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # result card
    st.markdown("</div>", unsafe_allow_html=True)  # app-shell
