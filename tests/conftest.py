"""Test setup: use a fresh SQLite TEST database, never the dev app.db.

Must set DATABASE_URL BEFORE importing the app, because the engine is
created at import time from the environment.
"""
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix="_test.db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def auth_headers(client, email="recruiter@test.com", password="secret123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (201, 400), r.text
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
