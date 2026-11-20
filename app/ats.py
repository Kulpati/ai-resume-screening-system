"""ATS readability score: can a machine read this resume well?

Separate from the JD match score. Match score = right skills for THIS job.
ATS score = is the resume itself complete and parseable, for ANY job.
Fixed rules, 100 points total - every point is explainable.
"""
from app.parsing import parse_resume


def ats_readability(text: str) -> dict:
    text = text or ""
    words = text.split()
    profile = parse_resume(text)
    low = text.lower()

    checks = {
        "has_email": 10 if profile["email"] else 0,
        "has_phone": 10 if profile["phone"] else 0,
        "has_skills_section": 15 if "skill" in low else 0,
        "has_education": 15 if profile["education"] else 0,
        "has_experience_or_projects": 15 if ("experience" in low or "project" in low) else 0,
        "good_length": 15 if len(words) >= 150 else (8 if len(words) >= 50 else 0),
        "has_numbers_or_metrics": 10 if any(ch.isdigit() for ch in text) else 0,
        "parseable_text": 10 if len(words) >= 20 else 0,
    }
    tips = []
    if not profile["email"]:
        tips.append("Add an email address - ATS cannot contact you without it.")
    if not profile["phone"]:
        tips.append("Add a phone number.")
    if "skill" not in low:
        tips.append("Add a clear 'Skills' section heading.")
    if not profile["education"]:
        tips.append("State your degree clearly (e.g. BTech, BSc).")
    if "experience" not in low and "project" not in low:
        tips.append("Add an 'Experience' or 'Projects' section.")
    if len(words) < 150:
        tips.append("Resume is very short - add detail on projects and skills.")
    if not any(ch.isdigit() for ch in text):
        tips.append("Add numbers/metrics (scores, counts, %) - recruiters and ATS look for them.")

    return {"ats_score": sum(checks.values()), "checks": checks, "tips": tips}
