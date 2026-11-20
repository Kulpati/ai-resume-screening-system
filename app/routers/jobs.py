"""Job routes + screening + ranking."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.insight import generate_insight
from app.scoring import score_resumes

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_owned_job(job_id: int, user, db: Session) -> models.Job:
    job = db.query(models.Job).filter(models.Job.id == job_id, models.Job.owner_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("", response_model=schemas.JobOut, status_code=201)
def create_job(payload: schemas.JobCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = models.Job(title=payload.title, description=payload.description, owner_id=user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Job).filter(models.Job.owner_id == user.id).all()


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return _get_owned_job(job_id, user, db)


@router.post("/{job_id}/screen")
def screen_job(job_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Score every COMPLETED resume owned by this user against this job."""
    job = _get_owned_job(job_id, user, db)
    resumes = (
        db.query(models.Resume)
        .filter(models.Resume.owner_id == user.id, models.Resume.status == models.ResumeStatus.COMPLETED.value)
        .all()
    )
    if not resumes:
        return {"job_id": job.id, "screened": 0, "results": []}

    scored = score_resumes(job.description, [r.extracted_text or "" for r in resumes])
    out = []
    for resume, s in zip(resumes, scored):
        row = (
            db.query(models.ScreeningResult)
            .filter(models.ScreeningResult.job_id == job.id, models.ScreeningResult.resume_id == resume.id)
            .first()
        )
        if not row:
            row = models.ScreeningResult(job_id=job.id, resume_id=resume.id)
            db.add(row)
        row.score = s["score"]
        row.matched_keywords = json.dumps(s["matched_keywords"])
        row.missing_keywords = json.dumps(s["missing_keywords"])
        out.append({"resume_id": resume.id, "filename": resume.filename, "score": s["score"]})
    db.commit()
    out.sort(key=lambda x: x["score"], reverse=True)
    return {"job_id": job.id, "screened": len(out), "results": out}


@router.get("/{job_id}/candidates/{resume_id}/ai-insight", response_model=schemas.AIInsightOut)
def ai_insight(job_id: int, resume_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = _get_owned_job(job_id, user, db)
    resume = db.query(models.Resume).filter(
        models.Resume.id == resume_id, models.Resume.owner_id == user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    result = db.query(models.ScreeningResult).filter(
        models.ScreeningResult.job_id == job.id,
        models.ScreeningResult.resume_id == resume.id,
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Not screened yet — run POST /jobs/{job_id}/screen first")

    def _loads(v):
        try:
            return json.loads(v) if v else []
        except Exception:
            return []

    insight = generate_insight(
        job_title=job.title,
        jd_text=job.description,
        resume_text=resume.extracted_text or "",
        filename=resume.filename,
        score=result.score,
        matched=_loads(result.matched_keywords),
        missing=_loads(result.missing_keywords),
    )
    return {"job_id": job.id, "resume_id": resume.id, **insight}


@router.get("/{job_id}/ranking", response_model=list[schemas.RankingItem])
def ranking(job_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = _get_owned_job(job_id, user, db)
    rows = (
        db.query(models.ScreeningResult)
        .filter(models.ScreeningResult.job_id == job.id)
        .order_by(models.ScreeningResult.score.desc())
        .all()
    )
    items = []
    for r in rows:
        resume = db.query(models.Resume).filter(models.Resume.id == r.resume_id).first()
        items.append({
            "resume_id": r.resume_id,
            "filename": resume.filename if resume else "",
            "score": r.score,
            "matched_keywords": r.matched_keywords,
            "missing_keywords": r.missing_keywords,
        })
    return items
