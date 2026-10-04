"""Real accounts: registration, login, passwords, roles."""
from sqlalchemy import select

from app.database import SessionLocal
from app.models import User
from app.security import hash_password, verify_password
from tests.conftest import EMAILS, PASSWORD


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=False)


def register(client, **overrides):
    data = {"name": "Sam", "email": "sam@test.example", "password": "a-long-password", "confirm": "a-long-password"}
    data.update(overrides)
    return client.post("/register", data=data, follow_redirects=False)


def test_login_success_goes_to_right_home(client):
    assert login(client, EMAILS[2], PASSWORD).headers["location"] == "/patient"
    other = type(client)(client.app)
    assert login(other, EMAILS[1], PASSWORD).headers["location"] == "/psychologist"


def test_login_is_case_insensitive_for_email(client):
    assert login(client, EMAILS[2].upper(), PASSWORD).status_code == 303


def test_wrong_password_and_unknown_email_look_the_same(client):
    wrong = login(client, EMAILS[2], "nope-nope-nope")
    unknown = login(client, "nobody@test.example", "nope-nope-nope")
    assert wrong.status_code == unknown.status_code == 401
    assert "Email or password is incorrect." in wrong.text and "Email or password is incorrect." in unknown.text


def test_lockout_after_repeated_failures(client):
    for _ in range(5):
        login(client, EMAILS[2], "bad-password-1")
    r = login(client, EMAILS[2], PASSWORD)  # even the right password is refused while locked
    assert r.status_code == 429


def test_passwords_are_stored_hashed():
    with SessionLocal() as db:
        stored = db.scalar(select(User).where(User.id == 2)).password_hash
    assert PASSWORD not in stored and stored.startswith("scrypt$")
    assert verify_password(PASSWORD, stored) and not verify_password("wrong", stored)
    assert hash_password(PASSWORD) != hash_password(PASSWORD)  # random salt each time


def test_register_creates_patient_and_signs_in(client):
    r = register(client)
    assert r.status_code == 303 and r.headers["location"] == "/patient"
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "sam@test.example"))
    assert user.role == "patient" and not user.is_demo and "a-long-password" not in user.password_hash
    assert client.get("/patient/consent").status_code == 200  # signed in, but still needs consent


def test_cannot_register_as_psychologist(client):
    register(client, role="psychologist")  # extra form field must be ignored
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == "sam@test.example")).role == "patient"


def test_register_validation(client):
    assert register(client, password="short", confirm="short").status_code == 400
    assert register(client, confirm="different-password").status_code == 400
    assert register(client, email="not-an-email").status_code == 400
    assert register(client, name="  ").status_code == 400


def test_duplicate_email_rejected(client):
    assert register(client, email=EMAILS[2].upper()).status_code == 400


def test_registered_patient_cannot_see_others_entries(client):
    register(client)
    client.post("/patient/consent", data={"understood": "yes"})
    page = client.get("/patient/log").text
    assert "MAYA-SECRET-ENTRY" not in page and "JAMES-SECRET-ENTRY" not in page


def test_logout_ends_session(client):
    login(client, EMAILS[2], PASSWORD)
    client.post("/logout")
    assert client.get("/patient/log", follow_redirects=False).headers["location"] == "/"


# --- one-click demo buttons ---
def add_demo_users():
    from app.constants import DEMO_ACCOUNT_EMAILS
    with SessionLocal() as db:
        db.add_all([
            User(id=10, name="Demo Patient", role="patient", is_demo=True, email=DEMO_ACCOUNT_EMAILS["patient"], password_hash="x"),
            User(id=11, name="Demo Psych", role="psychologist", is_demo=True, email=DEMO_ACCOUNT_EMAILS["psychologist"], password_hash="x"),
        ])
        db.commit()


def test_demo_buttons_skip_signin(client):
    add_demo_users()
    r = client.post("/demo/patient", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/patient"
    assert client.get("/patient/consent").status_code == 200  # signed in
    assert client.get("/patient/log", follow_redirects=False).status_code == 303  # but consent is still required
    other = type(client)(client.app)
    assert other.post("/demo/psychologist", follow_redirects=False).headers["location"] == "/psychologist"
    assert other.get("/psychologist").status_code == 200


def test_demo_login_only_accepts_the_two_roles(client):
    add_demo_users()
    assert client.post("/demo/admin").status_code == 404
    assert client.post("/demo/3").status_code == 404  # can't be used to become an arbitrary user


def test_demo_buttons_off_when_setting_off(client, monkeypatch):
    from app import config
    add_demo_users()
    monkeypatch.setattr(config, "SHOW_DEMO_LOGINS", False)
    assert client.post("/demo/patient").status_code == 404
    assert "Explore as" not in client.get("/").text


def test_demo_buttons_shown_on_login_page(client):
    page = client.get("/").text
    assert "Explore as patient" in page and "Explore as psychologist" in page


def test_get_not_allowed_on_demo_route(client):
    assert client.get("/demo/patient").status_code == 405
