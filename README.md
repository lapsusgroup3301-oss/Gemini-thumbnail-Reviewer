<p align="center">
  <h1>Gemini Thumbnail Reviewer</h1>
</p>

<p align="center">
  A multi-agent thumbnail analysis system built with FastAPI, Streamlit, and Google Gemini.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/FastAPI-Backend-green.svg">
  <img src="https://img.shields.io/badge/Streamlit-Frontend-red.svg">
  <img src="https://img.shields.io/badge/Gemini-API-orange.svg">
  <img src="https://img.shields.io/badge/License-GPLv3-lightgrey.svg">
</p>

---

## Overview

Gemini Thumbnail Reviewer is a multi-agent system that evaluates YouTube thumbnails by combining heuristic scoring and Gemini-powered visual reasoning.  
The backend runs on FastAPI and processes the analysis, while the frontend uses Streamlit to present clear, structured feedback.

The project was created as part of the Google Generative AI Capstone.

---

## Features

- Vision analysis using Google Gemini  
- Heuristic brightness, contrast and aspect-ratio scoring  
- Coach agent that merges reasoning from all agents  
- Per-session memory  
- Lightweight logging and metrics  
- Clean, interactive Streamlit UI  
- Backend and frontend separated clearly  

---

## Architecture

```
                ┌──────────────────────────┐
                │       Streamlit UI       │
                │  (upload, display data)  │
                └─────────────┬────────────┘
                              │
                              ▼
                ┌──────────────────────────┐
                │        FastAPI API       │
                │  /analyze endpoint       │
                └─────────────┬────────────┘
                              │
       ┌──────────────────────┼────────────────────────┐
       │                      │                        │
       ▼                      ▼                        ▼
┌───────────────┐     ┌───────────────┐       ┌────────────────┐
│  Vision Agent  │     │ Heuristic     │       │  Coach Agent   │
│  Gemini Model  │     │ Scoring       │       │ (Gemini)       │
└───────────────┘     └───────────────┘       └────────────────┘
       │                      │                        │
       └──────────────────────┴─────────┬──────────────┘
                                         ▼
                         ┌──────────────────────────┐
                         │ Combined Review Response │
                         └──────────────────────────┘
```

---

## Project structure

```
backend/
  app/
    agents/
    jobs/
    memory/
    ai_gemini.py
    gemini_client.py
    logging_config.py
    main.py
    models.py
    scoring.py
    requirements.txt

frontend/
  app.py
  requirements.txt

test_thumbnails/
  sample1.png
  sample2.jpg
  sample3.png
  ...

.env.example
.gitignore
LICENSE
README.md
```

---

## Test Thumbnails

A `eval_thumbnails/` folder is included at the project root.  
It contains PNG and JPG thumbnail examples that can be used to quickly test the reviewer without uploading your own images.

You can upload any file from that folder through the Streamlit interface to confirm that the system works correctly.

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

Copy the example file:

```
cp .env.example .env
```

Then open `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_key_here
```

---

# Running the project

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

Start by uploading any image from the `test_thumbnails/` folder to confirm the pipeline is functioning.

---

# How it works

### Vision Agent
Extracts visual features using Gemini (colors, subjects, theme cues, emotional tone).

### Heuristic Agent
Computes:
- brightness  
- contrast  
- aspect ratio fit  
- clarity markers  

### Coach Agent
Uses Gemini to produce:
- strengths  
- weaknesses  
- improvement suggestions  
- redesign prompts  

The backend merges agent results into a clean response, which the frontend displays.

---

# License

This project is released under the GPL v3 license.  
See the LICENSE file for full terms.

