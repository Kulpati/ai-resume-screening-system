"""Layer 2 AI: candidate insight — strengths, gaps, interview questions, verdict.

Works 100% OFFLINE. No API key, no internet, no LLM call.
The generation is template + rule based on top of Layer 1 (TF-IDF):
matched skills become strengths + proof questions, missing skills
become gaps + probe questions.

OPTIONAL LLM HOOK (not required, not used by default):
if OPENAI_API_KEY is set, `maybe_llm_enhance()` is where a real LLM
call *could* rewrite `summary` more fluently. The endpoint works
fully without it — see the stub at the bottom of this file.
"""
import os
import re
from collections import Counter

from app.scoring import tokenize

IMPORTANT_SKILLS = [
    "python", "fastapi", "postgresql", "sql", "rest", "api", "apis", "jwt",
    "authentication", "docker", "sqlalchemy", "pydantic", "pytest", "testing",
    "redis", "git", "linux", "alembic", "uvicorn",
]

QUESTION_TEMPLATES = {
    "fastapi": "Explain dependency injection in FastAPI with an example from your project.",
    "postgresql": "In PostgreSQL, when would you add an index, and what is the cost of adding one?",
    "python": "Explain how you used Python in your backend project — what was the hardest bug and how did you debug it?",
    "jwt": "How does JWT authentication work in your project? Where do you verify the token on each request?",
    "authentication": "Walk me through your login flow end to end — hashing, token creation, and token verification.",
    "docker": "What does your Dockerfile / docker-compose actually do? Which services run and how do they talk to each other?",
    "rest": "What makes an API RESTful in your project? Show one endpoint and its correct HTTP status codes.",
    "api": "Show one API endpoint you built. What happens on invalid input — which error and status code?",
    "apis": "Show one API endpoint you built. What happens on invalid input — which error and status code?",
    "sqlalchemy": "How do SQLAlchemy models map to database tables in your code? Show a query with a filter and a join.",
    "sql": "Write a SQL query with a JOIN and a WHERE filter. When would you use an index here?",
    "pydantic": "How does Pydantic validation protect your API from bad input? Give one example schema.",
    "pytest": "Show one test you wrote with pytest. What does it prove, and what would break if it failed?",
    "testing": "Show one automated test you wrote. What does it prove, and what would break if it failed?",
    "redis": "Where did you use Redis and why — what would be slower or broken without it?",
    "git": "Explain your Git workflow for this project: branches, commits, and how you would undo a bad commit.",
    "linux": "Which Linux commands do you actually use while developing and deploying this project?",
    "alembic": "Why use Alembic migrations instead of creating tables directly? Walk through one migration.",
    "uvicorn": "What is Uvicorn's role — what happens between an HTTP request arriving and FastAPI handling it?",
}

GENERIC_QUESTIONS = [
    "Walk me through this project in 2 minutes — problem, your design, and the hardest part.",
    "If this system had to handle 100x more resumes, what would break first and how would you fix it?",
    "Show the code you are most proud of in this project and explain why.",
    "How did you test this project, and how do you know the ranking is correct?",
    "What would you build next in this project if you had one more week, and why?",
]


def verdict_for_score(score: float) -> str:
    """One-line verdict from fixed, explainable score bands."""
    if score >= 70:
        return "Strong match — shortlist for interview"
    if score >= 45:
        return "Can interview — probe the gaps in the interview"
    return "Weak match — likely reject for this role"


def _context_for(skill: str, resume_text: str) -> str:
    """First resume line/sentence mentioning the skill = evidence, not a claim."""
    parts = re.split(r"[\n\.]+", resume_text or "")
    for part in parts:
        if skill in part.lower():
            ctx = " ".join(part.split())[:160]
            if ctx:
                return ctx
    return f"Mentioned in resume: {skill}"


def _rank_skills(skills: list[str], jd_text: str) -> list[str]:
    """Important skills first, then most frequent in the JD."""
    jd_counts = Counter(tokenize(jd_text))

    def key(skill):
        important_rank = IMPORTANT_SKILLS.index(skill) if skill in IMPORTANT_SKILLS else 999
        return (important_rank, -jd_counts.get(skill, 0))

    return sorted(skills, key=key)


def _question_for(skill: str, kind: str) -> str:
    base = QUESTION_TEMPLATES.get(skill)
    if base:
        return base if kind == "matched" else f"[Gap probe] This role needs {skill}, which was not found in the resume. Ask: {base}"
    if kind == "matched":
        return f"You mention {skill} in your resume — explain it with a concrete example from your project."
    return f"[Gap probe] This role needs {skill}, which was not found in the resume. Ask the candidate to explain {skill} and how they would learn/apply it here."


def maybe_llm_enhance(summary: str) -> str:
    """OPTIONAL stub — never required by the endpoint."""
    if not os.getenv("OPENAI_API_KEY"):
        return summary
    return summary


def generate_insight(job_title: str, jd_text: str, resume_text: str,
                     filename: str, score: float,
                     matched: list[str], missing: list[str]) -> dict:
    """Build the full insight object for one candidate vs one job."""
    ranked_matched = _rank_skills(matched, jd_text)
    ranked_missing = _rank_skills(missing, jd_text)

    strengths = [
        {"skill": s, "context": _context_for(s, resume_text)}
        for s in ranked_matched[:8]
    ]
    gaps = ranked_missing[:8]

    questions = []
    for s in ranked_matched[:3]:
        questions.append(_question_for(s, "matched"))
    for s in ranked_missing[:3]:
        q = _question_for(s, "missing")
        if q not in questions:
            questions.append(q)
    for q in GENERIC_QUESTIONS:
        if len(questions) >= 5:
            break
        if q not in questions:
            questions.append(q)
    questions = questions[:7]

    verdict = verdict_for_score(score)
    summary = (
        f"{filename} scored {score}/100 for '{job_title}'. "
        f"Verdict: {verdict}. "
        f"Matched {len(matched)} JD keywords, missing {len(missing)}."
    )
    summary = maybe_llm_enhance(summary)

    return {
        "job_title": job_title,
        "filename": filename,
        "score": score,
        "verdict": verdict,
        "summary": summary,
        "strengths": strengths,
        "gaps": gaps,
        "interview_questions": questions,
    }
