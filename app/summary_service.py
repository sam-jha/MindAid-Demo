"""Generating and saving a summary. Only ever called when a psychologist clicks a button."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, Summary, User
from app.summarisers import get_summariser
from app.summarisers.base import SummaryBlocked


def generate_summary(db: Session, patient: User) -> Summary | None:
    """Summarise ALL of the patient's entries and save the result. Returns None if no entries."""
    entries = db.scalars(
        select(Entry).where(Entry.patient_id == patient.id).order_by(Entry.created_at)
    ).all()
    if not entries:
        return None
    try:
        content = get_summariser().summarise(list(entries))  # may raise NotImplementedError / SummariserError
    except SummaryBlocked as err:
        # Record that the AI was blocked, so this patient is surfaced for a human to read
        # (a blocked summary is NOT an assessment, and the screen says so). Then tell the caller.
        db.add(Summary(
            patient_id=patient.id, generated_by="foundry:blocked",
            entries_covered_from=entries[0].created_at, entries_covered_to=entries[-1].created_at,
            content={"narrative": str(err), "themes": [], "mood_pattern": "Not assessed.",
                     "concerning_content": [], "priority": {"level": "blocked", "reason": "AI summary blocked - read the raw entries."},
                     "suggested_session_focus": "Read the raw entries.",
                     "uncertainty_note": "No AI analysis was produced.", "generated_by": "foundry:blocked"},
            priority_level="blocked", priority_reason="AI summary blocked by the content filter - read the raw entries."))
        db.commit()
        raise
    summary = Summary(
        patient_id=patient.id,
        generated_by=content["generated_by"],
        entries_covered_from=entries[0].created_at,
        entries_covered_to=entries[-1].created_at,
        content=content,
        priority_level=content["priority"]["level"],
        priority_reason=content["priority"]["reason"],
    )
    db.add(summary)
    db.commit()
    return summary
