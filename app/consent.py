"""Builds the consent notice. Storage and AI wording is generated from the REAL config,
so the notice can never claim something the running app doesn't do.
If you change the wording, bump CONSENT_NOTICE_VERSION in constants.py."""
from app import config


def storage_text() -> str:
    if config.DATABASE_URL.startswith("sqlite"):
        return ("Your entries are stored in a database file (SQLite) on the computer "
                "that is running this app.")
    return ("Your entries are stored in a managed database run by whoever hosts this app.")


def summary_text() -> str:
    if config.SUMMARISER_MODE == "fake":
        return ("Summaries in this prototype are placeholders. No text from your entries is "
                "sent anywhere, and no real analysis is done.")
    if config.SUMMARISER_MODE == "foundry":
        where = f" The model runs in the {config.AZURE_AI_REGION} region." if config.AZURE_AI_REGION else ""
        return ("When your psychologist generates a summary, the text of your entries is sent "
                "to an AI model hosted on Microsoft Azure AI Foundry to write that summary." + where +
                " Microsoft's standard terms apply, which can include temporary storage of requests "
                "for abuse monitoring. The AI can make mistakes.")
    # Fail loudly rather than show a notice that might be untrue.
    raise ValueError(f"Unknown SUMMARISER_MODE: {config.SUMMARISER_MODE!r}")


def notice_points() -> list[dict]:
    """Each point is a bold title plus a plain-language sentence or two."""
    return [
        {"title": "This is a prototype",
         "body": "MindAId is a portfolio project, not a real clinical tool."},
        {"title": "Where your entries are stored", "body": storage_text()},
        {"title": "Who can read them",
         "body": "A psychologist can read ALL of your entries, and can generate an AI summary "
                 "whenever they choose. You will not see the summary first."},
        {"title": "Where summary text goes", "body": summary_text()},
        {"title": "Keep it low-stakes",
         "body": "Don't write anything you wouldn't be comfortable existing in a test database."},
        {"title": "Nobody is watching live",
         "body": "Nobody monitors this app in real time. It is not therapy and it is not "
                 "crisis support."},
        {"title": "Support",
         "body": "If you need help now, see the support numbers at the bottom of every page."},
    ]
