"""Patients can't see each other's entries; roles can't cross over."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import Entry, Summary
from tests.conftest import acknowledge


def test_patients_only_see_their_own_entries(maya, james):
    acknowledge(maya)
    acknowledge(james)
    maya_page = maya.get("/patient/log").text
    james_page = james.get("/patient/log").text
    assert "MAYA-SECRET-ENTRY" in maya_page and "JAMES-SECRET-ENTRY" not in maya_page
    assert "JAMES-SECRET-ENTRY" in james_page and "MAYA-SECRET-ENTRY" not in james_page


def test_delete_all_only_deletes_own_entries(maya, james):
    acknowledge(maya)
    acknowledge(james)
    maya.post("/patient/delete")
    with SessionLocal() as db:
        texts = db.scalars(select(Entry.text)).all()
    assert "MAYA-SECRET-ENTRY" not in texts and "JAMES-SECRET-ENTRY" in texts


def test_patient_cannot_open_psychologist_pages(maya):
    acknowledge(maya)
    for url in ["/psychologist", "/psychologist/patients/3"]:
        r = maya.get(url, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/"


def test_psychologist_cannot_open_patient_log(psychologist):
    assert psychologist.get("/patient/log", follow_redirects=False).status_code == 303


def test_logged_out_visitor_is_sent_to_picker():
    from fastapi.testclient import TestClient
    from app.main import app
    r = TestClient(app).get("/patient/log", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_psychologist_can_read_entries(psychologist):
    assert "JAMES-SECRET-ENTRY" in psychologist.get("/psychologist/patients/3").text


def test_summary_only_created_when_psychologist_clicks(psychologist):
    psychologist.get("/psychologist")
    psychologist.get("/psychologist/patients/3")
    with SessionLocal() as db:
        assert db.scalar(select(Summary)) is None  # just looking never generates one
    psychologist.post("/psychologist/patients/3/summarise")
    with SessionLocal() as db:
        assert db.scalar(select(Summary)) is not None


def test_fake_summariser_never_pretends_to_analyse_real_text(psychologist):
    psychologist.post("/psychologist/patients/3/summarise")
    page = psychologist.get("/psychologist/patients/3").text
    assert "FAKE SUMMARISER - placeholder output, no analysis performed" in page
    assert "AI-generated - verify against the raw entries" in page
    with SessionLocal() as db:
        assert db.scalar(select(Summary)).priority_level == "unassessed"
