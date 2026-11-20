"""End-to-end: register -> login -> create job -> upload 3 resumes ->
screen -> ranking (strong > weak, scores 0-100) -> AI insight."""
from tests.conftest import auth_headers

JD = (
    "Backend Developer. Backend developer builds backend services in Python with FastAPI. "
    "Design REST API endpoints backed by PostgreSQL and SQL. Authentication uses JWT authentication. "
    "ORM is SQLAlchemy and validation is Pydantic. Database design, REST endpoints, testing with Pytest, "
    "deployment with Docker. Tools Git Linux Docker. Stack Python FastAPI PostgreSQL SQL SQLAlchemy "
    "Pydantic JWT Pytest."
)
STRONG = (
    "Backend developer building backend services in Python with FastAPI. Built REST API endpoints "
    "backed by PostgreSQL and SQL. Implemented JWT authentication. ORM SQLAlchemy validation Pydantic "
    "database design REST endpoints testing with Pytest deployment with Docker. Tools Git Linux Docker "
    "Stack Python FastAPI PostgreSQL SQL SQLAlchemy Pydantic JWT Pytest."
)
MEDIUM = (
    "Python developer with Python and SQL experience. Built a REST API project using Python. "
    "Worked with PostgreSQL database basics and Git. Interested in backend APIs and testing Linux."
)
WEAK = (
    "Frontend hobbyist focused on HTML CSS drawing photo editing presentations typing data entry "
    "spreadsheets cooking travel social media marketing. No programming projects."
)


def _setup(client):
    import uuid
    h = auth_headers(client, email=f"user-{uuid.uuid4().hex[:8]}@test.com")
    r = client.post("/jobs", json={"title": "Backend Developer", "description": JD}, headers=h)
    assert r.status_code == 201, r.text
    job_id = r.json()["id"]
    ids = {}
    for name, text in [("strong.txt", STRONG), ("medium.txt", MEDIUM), ("weak.txt", WEAK)]:
        r = client.post("/resumes/upload", files={"file": (name, text, "text/plain")}, headers=h)
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "COMPLETED", r.json()
        ids[name] = r.json()["id"]
    r = client.post(f"/jobs/{job_id}/screen", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["screened"] == 3
    return h, job_id, ids


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_protected_route_requires_auth(client):
    assert client.get("/jobs").status_code == 401


def test_ranking_order_and_score_range(client):
    h, job_id, ids = _setup(client)
    r = client.get(f"/jobs/{job_id}/ranking", headers=h)
    assert r.status_code == 200, r.text
    ranking = r.json()
    assert len(ranking) == 3
    for item in ranking:
        assert 0 <= item["score"] <= 100
    scores = {item["filename"]: item["score"] for item in ranking}
    assert scores["strong.txt"] > scores["weak.txt"], scores
    assert scores["strong.txt"] > scores["medium.txt"] > scores["weak.txt"] or scores["strong.txt"] == max(scores.values()), scores
    assert [i["score"] for i in ranking] == sorted([i["score"] for i in ranking], reverse=True)
    assert ranking[0]["filename"] == "strong.txt"


def test_ai_insight_for_strong_candidate(client):
    h, job_id, ids = _setup(client)
    ranking = client.get(f"/jobs/{job_id}/ranking", headers=h).json()
    strong_score = next(i["score"] for i in ranking if i["filename"] == "strong.txt")
    r = client.get(f"/jobs/{job_id}/candidates/{ids['strong.txt']}/ai-insight", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["score"] == strong_score
    assert data["strengths"], "strong candidate must have strengths"
    assert any(s["skill"] == "fastapi" for s in data["strengths"]), data["strengths"]
    assert isinstance(data["gaps"], list)
    assert len(data["interview_questions"]) >= 5, data["interview_questions"]
    assert any("fastapi" in q.lower() for q in data["interview_questions"]), data["interview_questions"]
    if strong_score >= 70:
        assert data["verdict"].lower().startswith("strong match"), data["verdict"]
    elif strong_score >= 45:
        assert data["verdict"].lower().startswith("can interview"), data["verdict"]
    else:
        assert data["verdict"].lower().startswith("weak"), data["verdict"]


def test_ai_insight_before_screen_is_404(client):
    h = auth_headers(client, email="fresh@test.com")
    r = client.post("/jobs", json={"title": "X", "description": JD}, headers=h)
    job_id = r.json()["id"]
    r = client.post("/resumes/upload", files={"file": ("a.txt", STRONG, "text/plain")}, headers=h)
    resume_id = r.json()["id"]
    r = client.get(f"/jobs/{job_id}/candidates/{resume_id}/ai-insight", headers=h)
    assert r.status_code == 404
