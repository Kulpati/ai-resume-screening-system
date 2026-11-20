"""App entry point. Run: uvicorn app.main:app --reload"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse


from app.database import Base, engine
from app.routers import jobs, resumes, stats, users


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Screening & Candidate Ranking System", version="1.0.0")
app.include_router(users.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(stats.router)



@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "project": "AI Resume Screening & Candidate Ranking System",
        "docs": "/docs",
        "health": "/health",
        "scoring": "TF-IDF cosine similarity (pure Python) + keyword matching",
    }

@app.get("/app")
def frontend():
    """The one-page frontend, served by FastAPI itself (no separate server)."""
    return FileResponse(Path(__file__).parent / "static" / "index.html")
