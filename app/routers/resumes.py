"""Resume upload + list. Status flow: UPLOADED -> PROCESSING -> COMPLETED/FAILED."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.ats import ats_readability
from app.extract import extract_text
from app.ml_classifier import classify_resume
from app.parsing import parse_resume


router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/upload", response_model=schemas.ResumeOut, status_code=201)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not (file.filename or "").lower().endswith((".txt", ".pdf")):
        raise HTTPException(status_code=400, detail="Only .txt and .pdf resumes are supported")

    resume = models.Resume(
        owner_id=user.id,
        filename=file.filename,
        content_type=file.content_type,
        status=models.ResumeStatus.UPLOADED.value,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    resume.status = models.ResumeStatus.PROCESSING.value
    db.commit()
    
    try:
        raw = await file.read()
    # File validation: hard size cap (2 MB) - an oversized file is
    # marked FAILED with the reason, never processed or stored as text.
        MAX_RESUME_BYTES = 2 * 1024 * 1024
        if len(raw) > MAX_RESUME_BYTES:
           raise ValueError(f"File too large: {len(raw)} bytes (max {MAX_RESUME_BYTES})")
        if not raw:
           raise ValueError("Empty file")
        text = extract_text(file.filename, raw)

        if not text.strip():
            raise ValueError("No text could be extracted from the file")
        resume.extracted_text = text
        resume.status = models.ResumeStatus.COMPLETED.value
    except Exception as e:
        resume.status = models.ResumeStatus.FAILED.value
        resume.error_message = str(e)
    db.commit()
    db.refresh(resume)
    return resume


@router.get("", response_model=list[schemas.ResumeOut])
def list_resumes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(models.Resume).filter(models.Resume.owner_id == user.id).all()

@router.get("/duplicates")
def duplicate_resumes(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Find duplicate resumes: same extracted text (exact, after
    lowercasing + whitespace cleanup) uploaded more than once.
    Hashing the cleaned text makes the comparison fast and exact."""
    import hashlib
    groups: dict[str, list] = {}
    resumes = (
        db.query(models.Resume)
        .filter(models.Resume.owner_id == user.id, models.Resume.status == models.ResumeStatus.COMPLETED.value)
        .all()
    )
    for r in resumes:
        cleaned = " ".join((r.extracted_text or "").lower().split())
        if not cleaned:
            continue
        h = hashlib.sha256(cleaned.encode()).hexdigest()
        groups.setdefault(h, []).append({"resume_id": r.id, "filename": r.filename})
    duplicates = [g for g in groups.values() if len(g) > 1]
    return {"duplicate_groups": duplicates, "duplicate_count": sum(len(g) for g in duplicates)}


@router.get("/{resume_id}", response_model=schemas.ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume



@router.get("/{resume_id}/profile")
def resume_profile(resume_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Full candidate profile for ONE resume: structured parsing +
    ML category (Naive Bayes) + ATS readability. No screening needed."""
    resume = db.query(models.Resume).filter(models.Resume.id == resume_id, models.Resume.owner_id == user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    text = resume.extracted_text or ""
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "profile": parse_resume(text),
        "ml_category": classify_resume(text),
        "ats": ats_readability(text),
    }
