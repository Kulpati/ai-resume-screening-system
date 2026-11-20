"""Dashboard stats for the logged-in recruiter: counts, average score,
verdict bands, ML category distribution. All computed live from the DB."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.database import get_db
from app.ml_classifier import classify_resume

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(get_current_user)):
    jobs = db.query(models.Job).filter(models.Job.owner_id == user.id).all()
    resumes = db.query(models.Resume).filter(models.Resume.owner_id == user.id).all()
    job_ids = [j.id for j in jobs]
    results = []
    if job_ids:
        results = db.query(models.ScreeningResult).filter(models.ScreeningResult.job_id.in_(job_ids)).all()

    scores = [r.score for r in results]
    verdicts = {"strong": 0, "can_interview": 0, "weak": 0}
    for s in scores:
        if s >= 70:
            verdicts["strong"] += 1
        elif s >= 45:
            verdicts["can_interview"] += 1
        else:
            verdicts["weak"] += 1

    categories = {"BACKEND": 0, "DATA": 0, "FRONTEND": 0, "DEVOPS": 0, "UNKNOWN": 0}
    for r in resumes:
        if r.status == models.ResumeStatus.COMPLETED.value and r.extracted_text:
            categories[classify_resume(r.extracted_text)["category"]] += 1

    return {
        "total_jobs": len(jobs),
        "total_resumes": len(resumes),
        "total_screened": len(results),
        "average_score": round(sum(scores) / len(scores), 2) if scores else 0.0,
        "verdict_counts": verdicts,
        "category_counts": categories,
    }
