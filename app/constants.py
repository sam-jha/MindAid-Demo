"""Things that are easy to change in one place."""

# TODO(Sam): confirm support resources for the countries your testers are in.
# Each item is (name, details). Shown in the footer of every patient screen.
SUPPORT_RESOURCES = [
    ("Samaritans", "116 123 (UK, free, 24/7)"),
    ("In an emergency", "call 999"),
]

# Bump this whenever the consent notice wording changes (stored with each acknowledgement).
CONSENT_NOTICE_VERSION = "2"

# The one-click "explore the demo" buttons on the login page sign in as these seeded demo accounts.
# ".example" is a reserved domain that can never be a real address.
DEMO_ACCOUNT_EMAILS = {
    "patient": "maya@demo.mindaid.example",
    "psychologist": "dr.rivera@demo.mindaid.example",
}
