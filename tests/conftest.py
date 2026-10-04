"""Test setup. Tests use their own throwaway SQLite file - never your real mindaid.db."""
import os
import tempfile

# Must be set BEFORE the app is imported, because the app reads settings at import time.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SUMMARISER_MODE"] = "fake"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app import security
from app.main import app
from app.models import Entry, User
from app.security import hash_password

PASSWORD = "test-password-123"
PASSWORD_HASH = hash_password(PASSWORD)  # hashed once; hashing is deliberately slow
EMAILS = {1: "dr@test.example", 2: "maya@test.example", 3: "james@test.example"}


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts with an empty database containing 1 psychologist and 2 patients."""
    security.clear_failures()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([
            User(id=1, name="Dr Test", role="psychologist", is_demo=True, email=EMAILS[1], password_hash=PASSWORD_HASH),
            User(id=2, name="Maya Test", role="patient", is_demo=True, email=EMAILS[2], password_hash=PASSWORD_HASH),
            User(id=3, name="James Test", role="patient", is_demo=True, email=EMAILS[3], password_hash=PASSWORD_HASH),
        ])
        db.add_all([
            Entry(patient_id=2, text="MAYA-SECRET-ENTRY", is_demo=False),
            Entry(patient_id=3, text="JAMES-SECRET-ENTRY", is_demo=False),
        ])
        db.commit()


def make_client(user_id: int) -> TestClient:
    """A browser-like client that is signed in as the given demo user."""
    client = TestClient(app)
    client.post("/login", data={"email": EMAILS[user_id], "password": PASSWORD})
    return client


@pytest.fixture
def maya():
    return make_client(2)


@pytest.fixture
def james():
    return make_client(3)


@pytest.fixture
def psychologist():
    return make_client(1)


def acknowledge(client: TestClient):
    client.post("/patient/consent", data={"understood": "yes"})


@pytest.fixture
def client():
    """A signed-out browser."""
    return TestClient(app)
