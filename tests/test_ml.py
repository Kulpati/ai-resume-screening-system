"""Unit + API tests for the upgrade layer: Naive Bayes classifier,
structured parsing, ATS readability, and the /profile endpoint."""
from app.ats import ats_readability
from app.ml_classifier import classify_resume
from app.parsing import parse_resume
from tests.conftest import auth_headers

RESUME = (
    "Rahul Sharma\n"
    "rahul@test.com 9876543210\n"
    "Skills: Python FastAPI Docker PostgreSQL\n"
    "Education: BTech, 2 years experience building REST APIs with projects"
)


def test_classifier_backend():
    r = classify_resume("Python FastAPI developer built REST APIs with PostgreSQL, JWT auth and Docker")
    assert r["category"] == "BACKEND"
    assert r["confidence"] > 50
    assert abs(sum(r["scores"].values()) - 100) < 0.1


def test_classifier_frontend_and_data():
    assert classify_resume("React TypeScript frontend UI components HTML CSS responsive design hooks")["category"] == "FRONTEND"
    assert classify_resume("Python pandas numpy machine learning data analysis dataset model training")["category"] == "DATA"


def test_classifier_empty_is_unknown():
    r = classify_resume("")
    assert r["category"] == "UNKNOWN"
    assert r["confidence"] == 0.0


def test_parse_resume_fields():
    p = parse_resume(RESUME)
    assert p["name"] == "Rahul Sharma"
    assert p["email"] == "rahul@test.com"
    assert p["phone"] == "9876543210"
    assert "python" in p["skills"] and "fastapi" in p["skills"]
    assert p["education"] == "BTech/BE"
    assert p["experience_years"] == 2.0


def test_ats_score_and_tips():
    good = ats_readability(RESUME + " " + ("project experience skills python " * 30))
    assert 0 <= good["ats_score"] <= 100
    assert good["ats_score"] >= 70
    bad = ats_readability("hello world")
    assert bad["ats_score"] < good["ats_score"]
    assert bad["tips"], "weak resume must produce improvement tips"


def test_profile_endpoint(client):
    h = auth_headers(client, email="profile@test.com")
    r = client.post("/resumes/upload", files={"file": ("rahul.txt", RESUME, "text/plain")}, headers=h)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    r = client.get(f"/resumes/{rid}/profile", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["profile"]["email"] == "rahul@test.com"
    assert data["ml_category"]["category"] == "BACKEND"
    assert 0 <= data["ats"]["ats_score"] <= 100
    assert client.get(f"/resumes/{rid}/profile").status_code == 401



def test_duplicates_and_dashboard(client):
    h = auth_headers(client, email="dup@test.com")
    for _ in range(2):
        r = client.post("/resumes/upload", files={"file": ("dup.txt", RESUME, "text/plain")}, headers=h)
        assert r.status_code == 201, r.text
    r = client.get("/resumes/duplicates", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["duplicate_count"] == 2, r.json()
    r = client.get("/stats/dashboard", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_resumes"] == 2
    assert d["category_counts"]["BACKEND"] == 2
    assert client.get("/stats/dashboard").status_code == 401



def test_upload_validation(client):
    h = auth_headers(client, email="valid@test.com")
    # Wrong type -> 400 before anything is stored
    r = client.post("/resumes/upload", files={"file": ("evil.docx", b"hello", "text/plain")}, headers=h)
    assert r.status_code == 400, r.text
    # Oversized (> 2 MB) -> stored as FAILED with a reason, never processed
    big = "x" * (2 * 1024 * 1024 + 1)
    r = client.post("/resumes/upload", files={"file": ("big.txt", big, "text/plain")}, headers=h)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "FAILED", r.json()
    assert "too large" in (r.json()["error_message"] or "").lower()


def test_frontend_page_served(client):
    r = client.get("/app")
    assert r.status_code == 200, r.text
    assert "AI Resume Screening" in r.text
    assert "/auth/login" in r.text
