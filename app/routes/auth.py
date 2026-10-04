"""Screen 1: sign in and create an account.
Patients can register themselves. Psychologist accounts are pre-made only, because a
psychologist can read ALL patients' entries (v1 has one shared demo psychologist)."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.constants import DEMO_ACCOUNT_EMAILS
from app.database import get_db
from app.models import User
from app.security import (clear_failures, hash_password, is_locked_out, record_failure,
                          verify_password, verify_unknown_user)
from app.session import get_current_user
from app.templating import templates

router = APIRouter()

MIN_PASSWORD_LENGTH = 10


def home_for(user: User) -> str:
    return "/patient" if user.role == "patient" else "/psychologist"


def login_page(request: Request, db: Session, error: str | None = None, email: str = "", status: int = 200):
    demo_users = []
    if config.SHOW_DEMO_LOGINS:
        demo_users = db.scalars(select(User).where(User.is_demo).order_by(User.role.desc(), User.name)).all()
    return templates.TemplateResponse(request, "login.html", {
        "error": error, "email": email, "demo_users": demo_users, "demo_password": config.DEMO_PASSWORD,
        "show_demo_buttons": config.SHOW_DEMO_LOGINS,
    }, status_code=status)


@router.get("/")
def home(request: Request, user: User | None = Depends(get_current_user), db: Session = Depends(get_db)):
    if user:
        return RedirectResponse(home_for(user), status_code=303)
    return login_page(request, db)


@router.post("/login")
def login(request: Request, email: str = Form(default=""), password: str = Form(default=""),
          db: Session = Depends(get_db)):
    email = email.strip().lower()
    if is_locked_out(email):
        return login_page(request, db, "Too many failed attempts. Please wait 15 minutes and try again.",
                          email, status=429)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_unknown_user(password)  # same delay as a real check
        ok = False
    else:
        ok = verify_password(password, user.password_hash)
    if not ok:
        record_failure(email)
        # Same message either way, so it doesn't reveal which emails have accounts.
        return login_page(request, db, "Email or password is incorrect.", email, status=401)
    clear_failures(email)
    request.session.clear()  # fresh session every login (this is what makes consent "every session")
    request.session["user_id"] = user.id
    return RedirectResponse(home_for(user), status_code=303)


@router.post("/demo/{role}")
def demo_login(role: str, request: Request, db: Session = Depends(get_db)):
    """One-click demo for visitors (e.g. employers): signs in as a fixed seeded demo account, no password.
    Only these two accounts, and only while SHOW_DEMO_LOGINS is on."""
    email = DEMO_ACCOUNT_EMAILS.get(role)
    user = db.scalar(select(User).where(User.email == email)) if config.SHOW_DEMO_LOGINS and email else None
    if user is None:
        raise HTTPException(status_code=404)
    request.session.clear()  # fresh session, so the patient still has to pass the consent screen
    request.session["user_id"] = user.id
    return RedirectResponse(home_for(user), status_code=303)


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None, "name": "", "email": ""})


@router.post("/register")
def register(request: Request, name: str = Form(default=""), email: str = Form(default=""),
             password: str = Form(default=""), confirm: str = Form(default=""),
             db: Session = Depends(get_db)):
    name, email = name.strip(), email.strip().lower()

    def fail(message: str):
        return templates.TemplateResponse(request, "register.html",
                                          {"error": message, "name": name, "email": email}, status_code=400)

    if not name or len(name) > 100:
        return fail("Please enter a name (up to 100 characters). A nickname is fine.")
    if "@" not in email or len(email) > 254:
        return fail("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        return fail(f"Your password needs at least {MIN_PASSWORD_LENGTH} characters.")
    if password != confirm:
        return fail("The two passwords don't match.")
    # Only patients can self-register. The role is set here on the server, never taken from the form.
    user = User(name=name, email=email, role="patient", is_demo=False, password_hash=hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return fail("An account with that email already exists. Try signing in.")
    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse("/patient", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)
