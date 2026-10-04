"""Creates the fictional demo users and their journal entries. Safe to run more than once.
    python scripts/seed.py            add anything missing
    python scripts/seed.py --reset    wipe demo entries + all summaries, then re-add them

The quoted lines in app/summarisers/fake.py (the fixed demo summaries) appear word-for-word
in the entries below. If you edit an entry, update the matching summary too."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app import config, models
from app.constants import DEMO_ACCOUNT_EMAILS
from app.database import Base, SessionLocal, engine
from app.security import hash_password

PSYCHOLOGIST = "Dr. Rivera (DEMO)"

# Demo logins. The password is DEMO_PASSWORD from .env (public on purpose - it is shown on the login page).
# ".example" is a reserved domain that can never be a real address.
DEMO_EMAILS = {
    "Dr. Rivera (DEMO)": DEMO_ACCOUNT_EMAILS["psychologist"],
    "Maya (DEMO)": DEMO_ACCOUNT_EMAILS["patient"],
    "James (DEMO)": "james@demo.mindaid.example",
    "Priya (DEMO)": "priya@demo.mindaid.example",
}

# patient name -> list of (days_ago, text). Days can be fractions (0.2 = about 5 hours ago).
DEMO_ENTRIES = {
    "Maya (DEMO)": [  # priority in the demo: notable
        (13, "First week of the new semester. Lots of reading and I'm already behind on the group project. Trying not to panic."),
        (11, "Couldn't fall asleep until nearly 3am again. My brain just keeps running through everything I haven't done."),
        (9, "Skipped lunch with Ana today. I keep cancelling on my friends because I just can't face people right now. I feel bad about it but also relieved."),
        (6, "Tried the breathing exercise from last session. It helped for about ten minutes and then the worry came back."),
        (3, "I've barely slept more than four hours most nights this week. I'm snapping at everyone and then feeling awful."),
        (1, "Mum phoned and I let it ring out. I don't know why I'm avoiding everyone. I just feel flat and tired all the time."),
    ],
    "James (DEMO)": [  # priority in the demo: urgent
        (14, "Meeting with the job centre went okay I suppose. They gave me a list of places to apply to."),
        (12, "Applied for three jobs today. Heard nothing back from any of the earlier ones. Had a few beers in the evening to take the edge off."),
        (10, "Another rejection email. Stayed in bed most of the day. Had more than a few beers again tonight."),
        (8, "Haven't replied to my brother's messages. I don't want him to see how bad things have got."),
        (5, "Drinking most evenings now. I know it isn't helping but it's the only thing that quiets my head."),
        (2, "I don't see the point in any of this anymore. Nothing I do makes any difference."),
        (0.2, "Sometimes I think everyone would be better off without me. I wrote that down and it scared me a bit, so I'm putting it here."),
    ],
    "Priya (DEMO)": [  # priority in the demo: routine
        (12, "Big presentation at work next Friday. Feeling nervous but also kind of excited."),
        (10, "Practised my slides in front of the mirror. Went for a walk afterwards and felt much calmer."),
        (8, "Slept badly last night because of nerves, but did the breathing exercises and fell back asleep."),
        (5, "Presentation went well! My manager said the data section was really clear. I'm proud of myself."),
        (3, "Coffee with my sister. We laughed a lot. I forget how much I need that."),
        (1, "A bit tired this week but generally okay. Planning to keep up the evening walks."),
    ],
}


def get_or_create_user(db, name: str, role: str) -> models.User:
    user = db.scalar(select(models.User).where(models.User.name == name))
    if not user:
        user = models.User(name=name, role=role, is_demo=True, email=DEMO_EMAILS[name], password_hash="")
        db.add(user)
    user.email = DEMO_EMAILS[name]
    user.password_hash = hash_password(config.DEMO_PASSWORD)  # keeps in step with DEMO_PASSWORD
    db.flush()
    return user


def main(reset: bool = False):
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        get_or_create_user(db, PSYCHOLOGIST, "psychologist")
        for name, entries in DEMO_ENTRIES.items():
            patient = get_or_create_user(db, name, "patient")
            if reset:  # only demo entries are removed; real entries typed by testers are kept
                db.execute(delete(models.Entry).where(models.Entry.patient_id == patient.id, models.Entry.is_demo))
                db.execute(delete(models.Summary).where(models.Summary.patient_id == patient.id))
            has_demo = db.scalar(select(models.Entry).where(models.Entry.patient_id == patient.id, models.Entry.is_demo))
            if not has_demo:
                for days_ago, text in entries:
                    db.add(models.Entry(patient_id=patient.id, text=text, is_demo=True,
                                        created_at=now - timedelta(days=days_ago)))
        db.commit()
    print("Demo users and entries ready.")


if __name__ == "__main__":
    main(reset="--reset" in sys.argv)
