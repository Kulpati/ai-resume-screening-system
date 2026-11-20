"""Structured parsing: pull a candidate profile out of raw resume text.

pyresparser-style, but pure Python (re only) and explainable:
every field is found by a visible rule - regex or keyword dictionary.
"""
import re

SKILL_DICTIONARY = [
    "python", "java", "javascript", "typescript", "golang", "c++",
    "fastapi", "django", "flask", "spring", "react", "angular", "vue",
    "node", "express", "nextjs", "html", "css", "tailwind", "redux",
    "postgresql", "mysql", "mongodb", "sqlite", "redis", "sql",
    "sqlalchemy", "pydantic", "jwt", "rest", "api", "graphql",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
    "linux", "git", "jenkins", "pytest", "testing", "pandas",
    "numpy", "tensorflow", "pytorch", "sklearn", "nlp", "spark",
    "hadoop", "etl", "tableau", "excel", "uvicorn", "alembic",
]

EDUCATION_KEYWORDS = [
    ("PhD", ["phd", "ph.d", "doctorate"]),
    ("MTech/ME", ["mtech", "m.tech", "master of technology"]),
    ("MBA", ["mba", "master of business"]),
    ("MSc/MS", ["msc", "m.sc", "master of science", " ms "]),
    ("BTech/BE", ["btech", "b.tech", "bachelor of technology", "b.e.", "bachelor of engineering"]),
    ("BSc", ["bsc", "b.sc", "bachelor of science"]),
    ("BCA", ["bca", "bachelor of computer"]),
    ("Diploma", ["diploma"]),
]


def _find_email(text: str):
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text or "")
    return m.group(0) if m else None


def _find_phone(text: str):
    m = re.search(r"(\+?\d{1,3}[\s-]?)?(\d{10})", (text or "").replace(" ", " "))
    if m:
        return m.group(0).strip()
    m2 = re.search(r"\+?\d[\d\s-]{9,14}\d", text or "")
    return m2.group(0).strip() if m2 else None


def _find_skills(text: str) -> list[str]:
    low = " " + (text or "").lower() + " "
    found = []
    for skill in SKILL_DICTIONARY:
        if re.search(r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])", low):
            found.append(skill)
    return found


def _find_education(text: str):
    low = " " + (text or "").lower() + " "
    for label, keys in EDUCATION_KEYWORDS:
        if any(k in low for k in keys):
            return label
    return None


def _find_experience_years(text: str):
    low = (text or "").lower()
    years = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)", low)]
    if years:
        return max(years)
    months = [float(x) for x in re.findall(r"(\d+)\s*(?:months?|mos?)", low)]
    if months:
        return round(max(months) / 12, 1)
    return None


def _find_name(text: str):
    for line in (text or "").splitlines():
        line = " ".join(line.strip().split())
        if not line or "@" in line or any(ch.isdigit() for ch in line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.replace(".", "").isalpha() for w in words):
            return line.title()
        return None
    return None


def parse_resume(text: str) -> dict:
    """Return the structured candidate profile for one resume text."""
    return {
        "name": _find_name(text),
        "email": _find_email(text),
        "phone": _find_phone(text),
        "skills": _find_skills(text),
        "education": _find_education(text),
        "experience_years": _find_experience_years(text),
    }
