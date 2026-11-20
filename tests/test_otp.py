"""Email OTP: disabled by default (demo never blocks), full flow when on."""
import app.config as config
from tests.conftest import auth_headers  # noqa: F401  (keeps conftest import path consistent)


def test_otp_disabled_by_default(client):
    r = client.post("/auth/send-otp", json={"email": "x@test.com"})
    assert r.status_code == 200, r.text
    assert r.json()["otp_enabled"] is False
    r = client.post("/auth/verify-otp", json={"email": "x@test.com", "code": "123456"})
    assert r.status_code == 400


def test_otp_full_flow(client, monkeypatch):
    sent = []
    monkeypatch.setattr(config, "OTP_ENABLED", True)
    monkeypatch.setattr("app.routers.users.send_otp_email", lambda e, c: sent.append(c) or True)

    r = client.post("/auth/send-otp", json={"email": "otp@test.com"})
    assert r.status_code == 200, r.text
    assert r.json()["otp_enabled"] is True
    assert len(sent) == 1 and len(sent[0]) == 6 and sent[0].isdigit()

    r = client.post("/auth/verify-otp", json={"email": "otp@test.com", "code": "000000" if sent[0] != "000000" else "111111"})
    assert r.status_code == 400, r.text  # wrong code rejected

    r = client.post("/auth/verify-otp", json={"email": "otp@test.com", "code": sent[0]})
    assert r.status_code == 200, r.text
    assert r.json()["verified"] is True

    r = client.post("/auth/verify-otp", json={"email": "otp@test.com", "code": sent[0]})
    assert r.status_code == 400, r.text  # a used code cannot be reused
