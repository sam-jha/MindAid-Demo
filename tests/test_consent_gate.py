"""The consent gate must be enforced by the SERVER, not just the browser."""
from sqlalchemy import select

from app import config
from app.database import SessionLocal
from app.models import ConsentAcknowledgement, Entry
from tests.conftest import acknowledge, make_client


def test_log_routes_blocked_without_consent(maya):
    for method, url in [("get", "/patient/log"), ("post", "/patient/log"),
                        ("get", "/patient/delete"), ("post", "/patient/delete")]:
        r = getattr(maya, method)(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/patient/consent", url


def test_blocked_post_does_not_save_entry(maya):
    maya.post("/patient/log", data={"text": "sneaky"})
    with SessionLocal() as db:
        assert db.scalar(select(Entry).where(Entry.text == "sneaky")) is None


def test_blocked_delete_does_not_delete(maya):
    maya.post("/patient/delete")
    with SessionLocal() as db:
        assert db.scalar(select(Entry).where(Entry.text == "MAYA-SECRET-ENTRY")) is not None


def test_consent_needs_the_tick_box(maya):
    r = maya.post("/patient/consent", data={}, follow_redirects=False)
    assert r.status_code == 400
    assert maya.get("/patient/log", follow_redirects=False).status_code == 303
    with SessionLocal() as db:
        assert db.scalar(select(ConsentAcknowledgement)) is None


def test_acknowledging_opens_log_and_is_stored(maya):
    acknowledge(maya)
    assert maya.get("/patient/log", follow_redirects=False).status_code == 200
    with SessionLocal() as db:
        row = db.scalar(select(ConsentAcknowledgement))
        assert row.user_id == 2 and row.notice_version and row.acknowledged_at


def test_consent_is_required_again_every_session(maya):
    acknowledge(maya)
    assert maya.get("/patient/log", follow_redirects=False).status_code == 200
    maya.post("/login", data={"email": "maya@test.example", "password": "test-password-123"})  # signing in again = a new session
    assert maya.get("/patient/log", follow_redirects=False).status_code == 303


def test_notice_matches_fake_config(maya):
    text = maya.get("/patient/consent").text
    assert "placeholders" in text and "Azure" not in text


def test_notice_matches_foundry_config(maya, monkeypatch):
    monkeypatch.setattr(config, "SUMMARISER_MODE", "foundry")
    assert "Azure AI Foundry" in maya.get("/patient/consent").text


def test_support_resources_in_footer(maya):
    acknowledge(maya)
    assert "116 123" in maya.get("/patient/log").text
    assert "116 123" in make_client(2).get("/patient/consent").text
