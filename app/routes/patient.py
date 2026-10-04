"""Screens 2 and 3: consent gate and the patient's journal log."""
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.consent import notice_points
from app.constants import CONSENT_NOTICE_VERSION
from app.database import get_db
from app.models import ConsentAcknowledgement, Entry, Summary, User
from app.session import require_role
from app.templating import templates

router = APIRouter(prefix="/patient")

MAX_ENTRY_LENGTH = 5000


def require_consent(request: Request, user: User = Depends(require_role("patient"))) -> User:
    """THE SERVER-SIDE GATE. Every log route depends on this. If the patient hasn't
    acknowledged the notice in THIS session, they are sent to the consent screen.
    (Logging in clears the session, so this applies every session.)"""
    if request.session.get("consent_version") != CONSENT_NOTICE_VERSION:
        raise HTTPException(status_code=303, headers={"Location": "/patient/consent"})
    return user


@router.get("")
def patient_home():
    return RedirectResponse("/patient/log", status_code=303)


@router.get("/consent")
def consent_page(request: Request, user: User = Depends(require_role("patient"))):
    return templates.TemplateResponse(
        request, "consent.html", {"user": user, "points": notice_points(), "error": None}
    )


@router.post("/consent")
def consent_submit(
    request: Request,
    understood: str = Form(default=""),
    user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    # The checkbox is also checked here, not just in the browser.
    if understood != "yes":
        return templates.TemplateResponse(
            request, "consent.html",
            {"user": user, "points": notice_points(), "error": "Please tick the box to continue."},
            status_code=400,
        )
    db.add(ConsentAcknowledgement(user_id=user.id, notice_version=CONSENT_NOTICE_VERSION))
    db.commit()
    request.session["consent_version"] = CONSENT_NOTICE_VERSION
    return RedirectResponse("/patient/log", status_code=303)


@router.get("/log")
def log_page(request: Request, user: User = Depends(require_consent), db: Session = Depends(get_db)):
    # Only THIS patient's entries (filtered by the logged-in user's id).
    entries = db.scalars(
        select(Entry).where(Entry.patient_id == user.id).order_by(Entry.created_at.desc())
    ).all()
    latest_summary = db.scalars(
        select(Summary).where(Summary.patient_id == user.id, Summary.priority_level != "blocked").order_by(Summary.generated_at.desc())
    ).first()
    return templates.TemplateResponse(
        request, "patient_log.html",
        {"user": user, "entries": entries, "summary_date": latest_summary.generated_at if latest_summary else None,
         "error": request.query_params.get("error")},
    )


@router.post("/log")
def add_entry(text: str = Form(default=""), user: User = Depends(require_consent), db: Session = Depends(get_db)):
    text = text.strip()
    if not text:
        return RedirectResponse("/patient/log?error=empty", status_code=303)
    if len(text) > MAX_ENTRY_LENGTH:
        return RedirectResponse("/patient/log?error=long", status_code=303)
    db.add(Entry(patient_id=user.id, text=text, is_demo=False))
    db.commit()
    return RedirectResponse("/patient/log", status_code=303)


@router.get("/delete")
def delete_confirm(request: Request, user: User = Depends(require_consent)):
    """The confirmation step before deleting everything."""
    return templates.TemplateResponse(request, "delete_confirm.html", {"user": user})


@router.post("/delete")
def delete_all(user: User = Depends(require_consent), db: Session = Depends(get_db)):
    db.execute(delete(Entry).where(Entry.patient_id == user.id))
    db.commit()
    return RedirectResponse("/patient/log", status_code=303)
