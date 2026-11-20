"""One-command demo: uses the samples/ files through the real API.

Run (server must be running — see README):
    python demo.py
Or let it boot its own test DB + TestClient (no server needed):
    python demo.py --offline
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent
SAMPLES = BASE / "samples"


def run(client):
    email, password = "demo@test.com", "secret123"
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    jd = (SAMPLES / "job_description_backend.txt").read_text()
    job = client.post("/jobs", json={"title": "Backend Developer", "description": jd}, headers=h).json()
    print(f"Job created: id={job['id']} title={job['title']}")

    ids = {}
    for name in ["resume_strong.txt", "resume_medium.txt", "resume_weak.txt"]:
        text = (SAMPLES / name).read_text()
        r = client.post("/resumes/upload", files={"file": (name, text, "text/plain")}, headers=h).json()
        ids[name] = r["id"]
        print(f"Uploaded {name}: status={r['status']}")

    print("Screen:", client.post(f"/jobs/{job['id']}/screen", headers=h).json())

    print("\n--- RANKING ---")
    for item in client.get(f"/jobs/{job['id']}/ranking", headers=h).json():
        print(f"{item['score']:>6}  {item['filename']}  matched={len(item['matched_keywords'])} missing={len(item['missing_keywords'])}")

    print("\n--- AI INSIGHT (strong candidate) ---")
    ins = client.get(f"/jobs/{job['id']}/candidates/{ids['resume_strong.txt']}/ai-insight", headers=h).json()
    print("Verdict:", ins["verdict"])
    print("Strengths:", [s["skill"] for s in ins["strengths"]])
    print("Gaps:", ins["gaps"])
    print("Interview questions:")
    for q in ins["interview_questions"]:
        print(" -", q)


if __name__ == "__main__":
    if "--offline" in sys.argv:
        import os, tempfile
        os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='_demo.db')}"
        from fastapi.testclient import TestClient
        from app.main import app
        with TestClient(app) as c:
            run(c)
    else:
        import httpx
        run(httpx.Client(base_url="http://127.0.0.1:8000"))
