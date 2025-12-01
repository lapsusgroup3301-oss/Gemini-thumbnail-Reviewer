# backend/app/main.py
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env automatically

from typing import Optional, Dict, Any, List

import asyncio
import base64
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    BackgroundTasks,
)
from fastapi.middleware.cors import CORSMiddleware

from .agents.vision_agent import run_vision_agent
from .agents.heuristic_agent import run_heuristic_agent
from .agents.coach_agent import run_coach_agent
from .agents.engagement_agent import run_engagement_agent

from .logging_config import log, get_metrics_snapshot
from .memory.memory import get_or_create_session, append_event, summarize_history
from .jobs.jobs import create_job, set_job_result, set_job_error, get_job


app = FastAPI(title="Gemini Thumbnail Reviewer AI", version="4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================
#                    MAIN ANALYSIS PIPELINE
# ==========================================================


@app.post("/api/v1/thumbnail/analyze")
async def analyze_thumbnail(
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    session_id: Optional[str] = Form(None),
    mode: str = Form("quick"),  # "quick" | "deep"
):
    """
    Run the complete analysis pipeline on one thumbnail.

    mode = "quick"  -> normal timeouts
    mode = "deep"   -> slightly longer timeouts so Gemini can think more.
    """
    try:
        # Read bytes & get session context
        img_bytes = await file.read()
        session_id = get_or_create_session(session_id)
        history_text = summarize_history(session_id)

        results: Dict[str, Any] = {}
        log.info(f"🚀 Starting thumbnail analysis pipeline (mode={mode})")

        # ---------------- 1. Vision Agent ----------------
        try:
            log.info("🧠 Running Vision Agent...")
            results["vision"] = await asyncio.wait_for(
                run_vision_agent(img_bytes),
                timeout=25 if mode == "quick" else 35,
            )
            log.info("✅ Vision Agent complete")
        except Exception as e:
            log.error(f"❌ Vision Agent failed: {e}")
            results["vision"] = {"agent": "vision", "error": str(e)}

        # ---------------- 2. Heuristic Agent -------------
        try:
            log.info("🔍 Running Heuristic Agent...")
            results["heuristic"] = await asyncio.wait_for(
                run_heuristic_agent(img_bytes, title, description),
                timeout=20,
            )
            log.info("✅ Heuristic Agent complete")
        except Exception as e:
            log.error(f"❌ Heuristic Agent failed: {e}")
            results["heuristic"] = {
                "agent": "heuristic",
                "error": str(e),
                "score": 0.0,
                "summary": "Heuristic analysis failed.",
                "details": [],
                "metrics": {},
            }

        # ---------------- 3. Coach Agent (Gemini) --------
        try:
            log.info("🎯 Running Coach Agent.")
            image_b64 = base64.b64encode(img_bytes).decode("utf-8")

            coach_result = await asyncio.wait_for(
                run_coach_agent(
                    title=title,
                    description=description,
                    vision=results.get("vision", {}),
                    heuristic=results.get("heuristic", {}),
                    history_summary=history_text,
                    image_b64=image_b64,
                ),
                timeout=45 if mode == "quick" else 60,
            )

            if not isinstance(coach_result, dict):
                coach_result = {
                    "agent": "coach",
                    "error": "Coach Agent returned invalid data",
                    "summary": str(coach_result)[:300],
                    "quality_score": 0.0,
                    "positives": [],
                    "improvements": [],
                }

            results["coach"] = coach_result
            log.info(
                "✅ Coach Agent complete (score: %s)",
                coach_result.get("quality_score", 0),
            )

        except asyncio.TimeoutError:
            log.error("⏰ Coach Agent timed out")
            results["coach"] = {
                "agent": "coach",
                "error": "Coach agent timeout",
                "summary": "Gemini analysis timed out.",
                "quality_score": 0.0,
                "positives": [],
                "improvements": [],
            }
        except Exception as e:
            log.error(f"❌ Coach Agent failed: {e}")
            results["coach"] = {
                "agent": "coach",
                "error": str(e),
                "summary": "",
                "quality_score": 0.0,
                "positives": [],
                "improvements": [],
            }

        # ---------------- 4. Engagement Agent ------------
        try:
            log.info("📈 Running Engagement Agent.")
            results["engagement"] = await asyncio.wait_for(
                run_engagement_agent(
                    vision=results.get("vision", {}),
                    heuristic=results.get("heuristic", {}),
                    coach_summary=results.get("coach", {}).get("summary", ""),
                ),
                timeout=15 if mode == "quick" else 20,
            )
            log.info("✅ Engagement Agent complete")
        except Exception as e:
            log.error(f"❌ Engagement Agent failed: {e}")
            results["engagement"] = {
                "agent": "engagement",
                "error": str(e),
                "engagement_score": 0.0,
                "summary": "Engagement analysis failed.",
            }

        # ---------------- 5. SCORING + REVIEW ------------
        try:
            heur_score = float(results.get("heuristic", {}).get("score", 0) or 0)
            coach = results.get("coach", {}) or {}
            coach_raw = float(coach.get("quality_score", 0) or 0)
            engage_score = float(
                results.get("engagement", {}).get("engagement_score", 0) or 0
            )

            # ---------- a) Map Gemini quality into 0–10 ----------
            # This stretches Gemini's 1–10 into a bit more aggressive 0–10.
            coach_score = 1.3 * coach_raw - 1.0
            coach_score = max(0.0, min(coach_score, 10.0))

            # ---------- b) Weighted blend ----------
            # Coach dominates, heuristics & engagement supplement.
            final_score = (
                coach_score * 0.65
                + heur_score * 0.15
                + engage_score * 0.20
            )

            # ---------- c) Modern-meta calibration ----------
            # If Gemini itself calls this modern/professional/clean/etc,
            # we treat it as creator-grade and bump above average.
            coach_text = (coach.get("summary") or "").lower()

            modern_keywords = [
                "modern",
                "professional",
                "clean",
                "cinematic",
                "high quality",
                "creator-grade",
                "well-designed",
                "already strong",
                "looks current",
                "contemporary",
                "polished",
                "strong thumbnail",
            ]

            if any(kw in coach_text for kw in modern_keywords):
                final_score += 1.2

            # Clamp & round
            final_score = round(max(0.0, min(final_score, 10.0)), 1)

            # ---------- d) Build designer-friendly review ----------
            model_summary = (coach.get("summary") or "").strip()

            if final_score >= 8.5:
                top_line = (
                    "Already a strong modern thumbnail; the ideas below are optional optimizations."
                )
            elif final_score >= 7.0:
                top_line = (
                    "Solid thumbnail that can be pushed further with a few targeted changes."
                )
            elif final_score >= 5.5:
                top_line = (
                    "Thumbnail is understandable, but needs visual upgrades to compete in today’s feed."
                )
            else:
                top_line = (
                    "Thumbnail needs a clearer, more modern redesign to feel competitive."
                )

            ai_line = (
                f"AI perspective: {model_summary}"
                if model_summary and model_summary.lower() not in top_line.lower()
                else ""
            )

            positives = coach.get("positives") or []
            improvements = coach.get("improvements") or []
            engagement = results.get("engagement", {}) or {}

            review: List[str] = []
            review.append(top_line)
            if ai_line:
                review.append(ai_line)

            if positives:
                review.append(
                    "Strengths: " + "; ".join(str(p) for p in positives[:3]) + "."
                )
            if improvements:
                review.append(
                    "Improvements: "
                    + "; ".join(str(i) for i in improvements[:4])
                    + "."
                )

            es = engagement.get("engagement_score")
            if es is not None:
                eng_line = engagement.get("summary") or f"Predicted engagement: {es}/10."
                review.append(f"Engagement outlook {es}/10 – {eng_line}")

            # ---------- e) Quick metrics for UI ----------
            heur_metrics = results.get("heuristic", {}).get("metrics", {}) or {}
            brightness = heur_metrics.get("brightness")
            contrast = heur_metrics.get("contrast")
            aspect_fit = heur_metrics.get("aspect_ratio_fit")

            meta = {
                "session_id": session_id,
                "heuristics": {
                    "brightness": round(float(brightness), 1)
                    if brightness is not None
                    else None,
                    "contrast": round(float(contrast), 1)
                    if contrast is not None
                    else None,
                    "aspect_ratio_fit": round(float(aspect_fit), 1)
                    if aspect_fit is not None
                    else None,
                },
                "agents": results,
                "gemini_used": "error" not in coach,
            }

            # ---------- f) Memory ----------
            append_event(
                session_id,
                {
                    "score": final_score,
                    "summary": model_summary or top_line,
                    "title": title,
                },
            )

            log.info(f"🏁 Analysis complete — Final Score: {final_score}/10")

            return {
                "status": "done",
                "score": final_score,
                "review": review,
                "meta": meta,
                "agents": results,
                "session_id": session_id,
            }

        except Exception as e:
            log.error(f"⚠️ Scoring failed: {e}")
            raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")

    except Exception as e:
        log.error(f"💥 Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")


# ==========================================================
#             OPTIONAL ASYNC JOB HANDLER
# ==========================================================


@app.post("/api/v1/thumbnail/analyze_async")
async def analyze_thumbnail_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(""),
    description: str = Form(""),
    session_id: Optional[str] = Form(None),
    mode: str = Form("deep"),
):
    """
    Async wrapper around analyze_thumbnail.
    """
    job_id = create_job()

    async def run_background():
        try:
            result = await analyze_thumbnail(file, title, description, session_id, mode)
            set_job_result(job_id, result)
        except Exception as e:
            set_job_error(job_id, str(e))

    background_tasks.add_task(run_background)
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ==========================================================
#                     METRICS + HEALTH
# ==========================================================


@app.get("/metrics")
async def metrics():
    return get_metrics_snapshot()


@app.get("/health")
async def health():
    return {"status": "ok", "agents": ["vision", "heuristic", "coach", "engagement"]}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
