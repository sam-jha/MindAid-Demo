"""Screens 4 and 5: the psychologist's patient list and patient view."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Entry, Summary, User
from app.session import require_role
from app.summarisers.base import SummariserError
from app.summary_service import generate_summary
from app.templating import templates

router = APIRouter(prefix="/psychologist")

def flash(request: Request, text: str) -> None:
    """One-time status message, kept in the session (not the URL, so links can't inject text)."""
    request.session["flash"] = text


# Lower number = shown first. "blocked" (AI refused, a human must read) sits just below urgent.
# "unassessed" and "no summary yet" sit together at the end.
PRIORITY_RANK = {"urgent": 0, "blocked": 1, "notable": 2, "routine": 3, "unassessed": 4, None: 4}


def latest_summary(db: Session, patient_id: int) -> Summary | None:
    return db.scalars(
        select(Summary).where(Summary.patient_id == patient_id).order_by(Summary.generated_at.desc())
    ).first()


def patient_rows(db: Session) -> list[dict]:
    """One dict per patient with everything the list screen needs."""
    rows = []
    for patient in db.scalars(select(User).where(User.role == "patient")):
        entries = db.scalars(select(Entry).where(Entry.patient_id == patient.id)).all()
        summary = latest_summary(db, patient.id)
        if summary:  # entries written after the last summary covered up to
            new_count = sum(1 for e in entries if e.created_at > summary.entries_covered_to)
        else:
            new_count = len(entries)
        rows.append({
            "patient": patient,
            "summary": summary,
            "level": summary.priority_level if summary else None,
            "latest_entry": max((e.created_at for e in entries), default=None),
            "new_count": new_count,
        })
    return rows


def sort_rows(rows: list[dict], sort: str) -> list[dict]:
    # Step 1: most recent entry first (patients with no entries go last).
    rows.sort(key=lambda r: (r["latest_entry"] is not None, r["latest_entry"] or 0), reverse=True)
    # Step 2 (priority sort only): a stable sort by priority keeps step 1's order within each level.
    if sort != "recent":
        rows.sort(key=lambda r: PRIORITY_RANK[r["level"]])
    return rows


@router.get("")
def patient_list(request: Request, sort: str = "priority",
                 user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    rows = sort_rows(patient_rows(db), sort)
    return templates.TemplateResponse(request, "psychologist_list.html", {
        "user": user, "rows": rows, "sort": sort,
        "any_new": any(r["new_count"] for r in rows),
        "message": request.session.pop("flash", None),
    })


@router.post("/summarise-all")
def summarise_all(request: Request, user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    done, failed = 0, []
    for row in patient_rows(db):
        if row["new_count"] > 0:
            try:
                generate_summary(db, row["patient"])
                done += 1
            except (NotImplementedError, SummariserError) as err:
                failed.append(f"{row['patient'].name} ({err})")  # one failure must not stop the others
    message = f"Generated {done} summaries."
    if failed:
        message += " Could not summarise: " + "; ".join(failed)
    flash(request, message)
    return RedirectResponse("/psychologist", status_code=303)


@router.get("/patients/{patient_id}")
def patient_view(patient_id: int, request: Request,
                 user: User = Depends(require_role("psychologist")), db: Session = Depends(get_db)):
    patient = db.get(User, patient_id)
    if patient is None or patient.role != "patient":
        raise HTTPException(status_code=404)
    entries = db.scalars(
        select(Entry).where(Entry.patient_id == patient.id).order_by(Entry.created_at.desc())
    ).all()
    summaries = db.scalars(
        select(Summary).where(Summary.patient_id == patient.id).order_by(Summary.generated_at.desc())
    ).all()
    return templates.TemplateResponse(request, "patient_view.html", {
        "user": user, "patient": patient, "entries": entries,
        "latest": summaries[0] if summaries else None, "previous": summaries[1:],
        "message": request.session.pop("flash", None),
    })


@router.post("/patients/{patient_id}/summarise")
def summarise_one(patient_id: int, request: Request, user: User = Depends(require_role("psychologist")),
                  db: Session = Depends(get_db)):
    patient = db.get(User, patient_id)
    if patient is None or patient.role != "patient":
        raise HTTPException(status_code=404)
    try:
        result = generate_summary(db, patient)
    except (NotImplementedError, SummariserError) as err:
        flash(request, str(err))
        return RedirectResponse(f"/psychologist/patients/{patient_id}", status_code=303)
    if result is None:
        flash(request, "No entries to summarise yet.")
        return RedirectResponse(f"/psychologist/patients/{patient_id}", status_code=303)
    return RedirectResponse(f"/psychologist/patients/{patient_id}", status_code=303)
