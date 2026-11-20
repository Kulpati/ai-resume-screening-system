"""Email OTP service: generate, hash, and send one-time codes.

Rules (the interview answer):
  - Code is 6 digits, generated with the `secrets` module (crypto-safe,
    not `random`).
  - Only the SHA-256 hash of (email + code) is stored in the DB - never
    the plain code, same rule as passwords.
  - A code lives 5 minutes and allows max 3 wrong attempts.
  - Sending uses SMTP when configured; without SMTP (local dev) the
    code is printed to the server console and False is returned.
"""
import hashlib
import secrets
import smtplib
from email.message import EmailMessage

from app import config


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, code: str) -> str:
    return hashlib.sha256(f"{email.lower()}:{code}".encode()).hexdigest()


def send_otp_email(email: str, code: str) -> bool:
    """Send the code by SMTP. Returns True only if actually emailed."""
    if not (config.SMTP_HOST and config.SMTP_USER and config.SMTP_PASSWORD):
        print(f"[OTP-DEV] OTP for {email}: {code} (SMTP not configured)")
        return False
    msg = EmailMessage()
    msg["Subject"] = "Your verification code - AI Resume Screening System"
    msg["From"] = config.SMTP_FROM
    msg["To"] = email
    msg.set_content(
        f"Your one-time verification code is: {code}\n"
        f"It expires in {config.OTP_EXPIRE_MINUTES} minutes. Do not share it."
    )
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
    return True
