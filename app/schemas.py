"""Pydantic request/response schemas."""
import json
from typing import List, Optional

from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobCreate(BaseModel):
    title: str
    description: str


class JobOut(BaseModel):
    id: int
    title: str
    description: str
    owner_id: int

    model_config = {"from_attributes": True}


class ResumeOut(BaseModel):
    id: int
    filename: str
    content_type: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    owner_id: int

    model_config = {"from_attributes": True}


class Strength(BaseModel):
    skill: str
    context: str


class AIInsightOut(BaseModel):
    job_id: int
    resume_id: int
    job_title: str
    filename: str
    score: float
    verdict: str
    summary: str
    strengths: List[Strength] = []
    gaps: List[str] = []
    interview_questions: List[str] = []


class RankingItem(BaseModel):
    resume_id: int
    filename: str
    score: float
    matched_keywords: List[str] = []
    missing_keywords: List[str] = []

    @field_validator("matched_keywords", "missing_keywords", mode="before")
    @classmethod
    def parse_json_list(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [x.strip() for x in v.split(",") if x.strip()]
        return v or []


class OTPRequest(BaseModel):
    email: str


class OTPVerify(BaseModel):
    email: str
    code: str
