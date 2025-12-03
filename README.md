# 🚀 Gemini Thumbnail Reviewer
A multi-agent YouTube thumbnail analysis system built with FastAPI, Streamlit, and Google Gemini.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/FastAPI-Backend-green.svg">
  <img src="https://img.shields.io/badge/Streamlit-Frontend-red.svg">
  <img src="https://img.shields.io/badge/Gemini-API-orange.svg">
  <img src="https://img.shields.io/badge/Multi--Agent-System-purple.svg">
</p>

---

## Overview

Gemini Thumbnail Reviewer is a full multi-agent system designed to evaluate and improve YouTube thumbnails.  
It combines LLM-powered visual reasoning with deterministic heuristics, session memory, and a structured coaching agent.

The system was built as part of the **Google Generative AI Agents Capstone**, which requires agents, tool use, memory, and observability.  
This project satisfies those requirements fully while remaining lightweight and easy to run locally.

---

## Key Features

### 🔍 Vision Analysis (Gemini Vision)
Automatically extracts:
- subject & layout structure  
- composition cues  
- emotional tone  
- color and lighting characteristics  
- style tags  
Used to understand *what the viewer actually sees* at a glance.

### 📊 Heuristic Metrics
Fast, deterministic scoring layer:
- brightness  
- contrast  
- aspect ratio fit  
- clarity markers  
Acts as a sanity check on LLM outputs and improves consistency.

### 🧠 Coach Agent (Gemini)
A structured JSON-only agent that:
- merges signals from all other agents  
- scores quality (0–10)  
- lists strengths and weaknesses  
- gives specific improvement suggestions  
- understands modern creator meta (MrBeast, Dhruv Rathee, Ryan Trahan…)  

### 🔁 Engagement Prediction Agent
Predicts CTR potential using:
- heuristic score  
- clarity metrics from vision  
- density of coach insights  

### 💾 Long-Term Memory
Each session stores:
- past thumbnails  
- scores  
- summaries  
- patterns in creator preferences  

This lets the system adapt to a creator’s style over time.

### 📈 Observability
Integrated:
- structured logs  
- timing metrics  
- error-safe agent isolation  

### 🖥 Clean Frontend/Backend Split
- FastAPI backend for analysis  
- Streamlit frontend for visualization  
- Fully decoupled architecture  

---

## Architecture

```
                      ┌──────────────────────────────┐
                      │         Streamlit UI          │
                      │    (upload + visualization)   │
                      └──────────────┬───────────────┘
                                     │
                                     ▼
                      ┌──────────────────────────────┐
                      │           FastAPI             │
                      │       /analyze endpoint       │
                      └──────────────┬───────────────┘
                                     │
        ┌────────────────────────────┼──────────────────────────────┐
        │                            │                              │
        ▼                            ▼                              ▼
┌────────────────┐        ┌───────────────────┐          ┌──────────────────────┐
│ Vision Agent   │        │ Heuristic Agent  │          │ Coach Agent (Gemini) │
│ (Gemini Vision)│        │ (Metrics Scoring)│          │ Multi-source Fusion   │
└────────────────┘        └───────────────────┘          └──────────────────────┘
        │                            │                              │
        └────────────────────────────┴─────────────────────┬────────┘
                                                           ▼
                                               ┌────────────────────────┐
                                               │ Engagement Agent       │
                                               │ CTR Score Prediction   │
                                               └────────────────────────┘
                                                           │
                                                           ▼
                                                ┌─────────────────────────┐
                                                │ Combined Review Output │
                                                └─────────────────────────┘
```

---

## Project Structure

```
backend/
  app/
    agents/
      coach_agent.py
      engagement_agent.py
      heuristic_agent.py
      vision_agent.py
    jobs/
      jobs.py
    memory/
      memory.py
      memory.store.json
    ai_gemini.py
    gemini_client.py
    logging_config.py
    main.py
    models.py
    scoring.py
    requirements.txt

eval_thumbnails/
  eval_labels.csv
  README.md

frontend/
  app.py
  requirements.txt

.env.example
```

---

## Test Thumbnails

A `eval_thumbnails/` folder is included for quick evaluation.  
You can upload these directly in the Streamlit UI to verify that the pipeline works correctly end-to-end.

---

# Setup

## 1. Clone the repository

```
git clone https://github.com/lapsusgroup3301-oss/Gemini-thumbnail-Reviewer.git
cd Gemini-thumbnail-Reviewer
```

---

## 2. Create a virtual environment

### Windows
```
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux
```
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

### Backend
```
pip install -r backend/app/requirements.txt
```

### Frontend
```
pip install -r frontend/requirements.txt
```

---

## 4. Setup environment variables

```
cp .env.example .env
```

Open `.env` and insert your Gemini key:

```
GEMINI_API_KEY=your_key_here
```

---

# Running the Project

## Backend (FastAPI)

```
uvicorn backend.app.main:app --reload
```

Runs at:
http://127.0.0.1:8000  

---

## Frontend (Streamlit)

```
streamlit run frontend/app.py
```

Runs at:
http://localhost:8501

Upload any image from `eval_thumbnails/` to test the pipeline.

---

# How It Works

### Vision Agent  
Gemini Vision model describes the visual scene, color, subjects, composition, and tags.

### Heuristic Agent  
Computes brightness, contrast, and aspect-ratio fitness.

### Coach Agent  
Combines all signals into a single structured review:
- verdict  
- strengths  
- weaknesses  
- realistic improvements  
- quality score  

### Engagement Agent  
Predicts performance potential using a blended scoring formula.

# ⚠️ API Key Setup method 2

When the backend and frontend are started without a proper `.env` file, the app displays an API Key dialog.  
This happens when:

- `.env` does not exist  
- `GEMINI_API_KEY` is missing or empty  

The dialog lets the user enter the Gemini API key directly in the UI.  
The key is stored **locally** inside the newly created `.env` file.  
It is never uploaded, logged, transmitted, or stored anywhere else.  
The backend reads it only from your local machine.

This system prevents startup errors and ensures the app works even if someone forgets to configure the environment manually.

**Short reassurance:**  
Your key never leaves your computer. The UI only writes it into `.env` and nothing more.

Manual setup is still available in the README and works the same way.

---
### Security Note

This application never sends your API key to any external server.  
The key you enter is written only to your local `.env` file in the `root` folder.  
The backend reads it directly from that file and uses it only for calling the Gemini API on your machine.

Your API key is not transmitted over the internet at any point.

# License

This project is licensed under GNU GPL v3.  
See the LICENSE file for full terms.
