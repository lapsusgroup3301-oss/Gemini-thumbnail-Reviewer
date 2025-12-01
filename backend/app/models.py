# backend/app/models.py

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class ThumbnailAnalysisRequest(BaseModel):
    image_b64: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    session_id: Optional[str] = None


class HeuristicMetrics(BaseModel):
    brightness: float
    contrast: float
    aspect_ratio_fit: float
    width: int
    height: int


class AgentOutput(BaseModel):
    agent: str
    summary: str
    details: List[str]


class ThumbnailAnalysisResponse(BaseModel):
    score: float
    metrics: HeuristicMetrics
    explanations: List[AgentOutput]
    suggestions: List[str]
    session_id: str
    job_id: Optional[str] = None
