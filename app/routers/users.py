"""Auth routes: register, login, me, email OTP verification."""
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import config, models, schemas
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.otp import generate_otp, hash_otp, send_otp_email


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=201)
def register(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = models.User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.Token)
def login(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user.id), "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/send-otp")
def send_otp(payload: schemas.OTPRequest, db: Session = Depends(get_db)):
    """Generate a 6-digit code, store only its hash, email the code.
    With OTP_ENABLED off this is a no-op that reports itself disabled,
    so the demo login flow is never blocked."""
    if not config.OTP_ENABLED:
        return {"otp_enabled": False, "message": "OTP verification is disabled"}
    code = generate_otp()
    row = db.query(models.EmailOTP).filter(models.EmailOTP.email == payload.email).first()
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.OTP_EXPIRE_MINUTES)
    if not row:
        row = models.EmailOTP(email=payload.email, code_hash=hash_otp(payload.email, code), expires_at=expires)
        db.add(row)
    else:
        row.code_hash = hash_otp(payload.email, code)
        row.attempts = 0
        row.expires_at = expires
    db.commit()
    sent = send_otp_email(payload.email, code)
    return {"otp_enabled": True, "email_sent": sent, "expires_in_minutes": config.OTP_EXPIRE_MINUTES}


@router.post("/verify-otp")
def verify_otp(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    """Check a code: must exist, be unexpired, match the stored hash,
    and stay within the attempt limit. A used code is deleted."""
    if not config.OTP_ENABLED:
        raise HTTPException(status_code=400, detail="OTP verification is disabled")
    row = db.query(models.EmailOTP).filter(models.EmailOTP.email == payload.email).first()
    if not row:
        raise HTTPException(status_code=400, detail="No OTP requested for this email")
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired - request a new one")
    if row.attempts >= config.OTP_MAX_ATTEMPTS:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=400, detail="Too many wrong attempts - request a new OTP")
    if not hmac.compare_digest(row.code_hash, hash_otp(payload.email, payload.code)):
        row.attempts += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Wrong OTP")
    db.delete(row)
    db.commit()
    return {"verified": True, "email": payload.email}
