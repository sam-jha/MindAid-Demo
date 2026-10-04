# MindAId (demo prototype)

**Live demo: https://mindaid-app.calmdune-35b6fddc.uksouth.azurecontainerapps.io**
No sign-up needed: on the login page click **Explore as psychologist** or **Explore as patient**.
(Fictional data only. The demo resets whenever the app restarts.)

A small portfolio prototype: patients write journal entries between therapy sessions, and a
psychologist can read them and click **Summarise** to generate an AI summary on demand.

**This is not a real clinical tool.** Every user and entry is fictional demo data. There are no
real accounts or passwords. Nobody monitors the app. Do not put real personal information in it.

## What it does

- **Sign in / create account:** real email + password accounts (passwords are stored as salted hashes, with a
  limit on repeated failed attempts). Visitors can register as patients. Psychologist accounts are pre-made
  only, because a psychologist can read all patients' entries. Pre-made demo accounts are listed on the login page.
- **Consent gate (patients):** a notice the patient must acknowledge *every* session before the
  log opens. It is enforced on the server, not just hidden in the page. The notice text is
  generated from the real settings, so it never claims something the app doesn't do.
- **Patient log:** write entries, see your own past entries, see when a summary was generated
  (not its content), delete all your entries. Support numbers show in the footer on every patient screen.
- **Psychologist list:** patients ordered by priority (urgent, notable, routine, not yet
  summarised), then most recent entry; "new entries" badges; "Summarise all with new entries".
- **Psychologist patient view:** raw entries, a Summarise button, the latest summary and earlier ones.
  Everything AI-generated is labelled "AI-generated - verify against the raw entries".
- **Summaries are never automatic** and the patient does not see them first.

Deliberately **not** built: matching, chatbot, messaging, notifications, real login, mood ratings,
multiple psychologists.

## Run it locally

You need Python 3.11 or newer (built with 3.12).

Run these one at a time. (Don't paste the "Why" notes - they're explanations, not commands.)

```bash
cd "MindAid Project"
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/seed.py
uvicorn app.main:app --reload
```

Why: `venv` creates a private Python environment (once); `source venv/bin/activate` switches it on
(every new terminal); `pip install` installs the libraries (once); `cp .env.example .env` creates your
local settings (once); `seed.py` creates the demo users and entries; `uvicorn` starts the app.

Open http://localhost:8000 . Stop with Ctrl+C. Health check: http://localhost:8000/health

To put the demo back to its starting state: `python scripts/seed.py --reset`
(removes demo entries and all summaries; entries a tester typed are kept).

## Run the tests

```bash
source venv/bin/activate
python -m pytest
```

The tests use their own temporary database, never your real one. They cover: the consent gate
cannot be bypassed (and is needed again every session), patients cannot see or delete each
other's entries, roles cannot cross over, and summaries are only created on a click.

## Settings (environment variables)

Listed in `.env.example`. The real `.env` is ignored by git and must never be committed.

| Setting | What it does | Default |
|---|---|---|
| `DATABASE_URL` | Where the database lives. SQLite file locally; a Postgres URL later. | `sqlite:///./mindaid.db` |
| `SUMMARISER_MODE` | `fake` (placeholders) or `foundry` (not built yet). | `fake` |
| `SECRET_KEY` | Signs the demo login cookie. | dev-only value |
| `PORT` | Port the server listens on. | `8000` |
| `COOKIE_SECURE` | `true` on HTTPS (Azure) so the login cookie is HTTPS-only. | `false` |
| `SHOW_DEMO_LOGINS` | Show the demo accounts + password on the login page. | `true` |
| `DEMO_PASSWORD` | Password for the pre-made demo accounts (public on purpose). | `demo-password-1` |

Support numbers live in [app/constants.py](app/constants.py). **TODO: confirm the right resources for each tester's country.**

## Where does data go? (plain English)

With the default settings, **nothing leaves your computer.**

| Data | Where it is stored | Who can see it |
|---|---|---|
| Journal entries | The `mindaid.db` file in this folder (SQLite) | The demo patient who wrote them, and the demo psychologist |
| Consent acknowledgements (who, which notice version, when) | Same file | Nobody in the app; stored as a record |
| Summaries | Same file | The demo psychologist. Patients only see *that* one was generated, and when |
| Accounts | Name, email and a salted password *hash* (never the password) in the same file. A signed cookie in your browser remembers you are signed in. | The app only; the psychologist list shows patient names, not emails |

- **Summaries (fake mode):** produced locally by `FakeSummariser`. No text is sent to any AI service.
  Demo patients get fixed fictional summaries; anyone else gets a labelled placeholder.
- **Summaries (foundry mode, not built yet):** the entry text would be sent to an AI model on Microsoft
  Azure AI Foundry. The consent notice already switches to say so when this mode is set.
- **Switching to a managed database later:** change `DATABASE_URL` (and add the matching database driver
  to `requirements.txt`). The consent notice then says entries are in a managed database.
- **Deleting:** "Delete all my entries" removes the patient's entries. It does *not* remove summaries
  already generated, and the confirmation screen says so.

## AI summaries with Azure AI Foundry

Set `SUMMARISER_MODE=foundry` and fill in the three `AZURE_AI_*` values in `.env` (plus `AZURE_AI_REGION`, which the
consent notice shows). The model is `gpt-4.1-mini`, deployed as a **Standard** (regional) deployment in UK South, so text
is processed in the UK. Every summary is checked by code before it is shown:

- Flagged quotes must match the patient's entries word for word; any that don't are kept but marked **Unverified**.
- An invalid priority becomes "unassessed". A fixed "this does not mean there is no risk" line is always added.
- If Azure's content filter blocks a summary (see below), the patient shows as **"AI blocked - read entries"**, just
  below Urgent, with a note that this is *not* an assessment.

**Known issue - content filter.** Azure's default self-harm filter blocks AI output that quotes statements like
"everyone would be better off without me", so the most concerning patients can fail to summarise. A custom filter
policy (`mindaid-selfharm-high`) is attached to the deployment, but Azure appears not to enforce a looser setting
without approval. To fix it properly, apply for Microsoft's *modified content filtering*
(https://aka.ms/oai/modifiedaccess). Until then the app retries up to 3 times and falls back to "read the raw entries".

## How it is built

- Python 3.12, FastAPI, Jinja2 server-rendered pages, plain CSS, SQLAlchemy + SQLite. One tiny script
  (greys out the Continue button until the box is ticked); everything important is checked on the server.
- `app/routes/` the screens - `app/models.py` the four tables - `app/consent.py` the notice text -
  `app/summarisers/` the one summarise interface, the fake, and the not-yet-built Foundry class -
  `scripts/seed.py` demo data - `tests/` automated tests.

## Docker (not deployed)

A `Dockerfile` is included for Azure Container Apps later. The app listens on `PORT` and has `/health`.
Nothing is deployed and no cloud resources are created.

```bash
docker build -t mindaid .
docker run -p 8000:8000 -e SECRET_KEY=some-long-random-string mindaid
```

Notes: a container's SQLite file is lost when the container is replaced, so a real deployment needs a
managed database. Run the seed script inside the container to create demo users.

## Deployed on Azure

Live at https://mindaid-app.calmdune-35b6fddc.uksouth.azurecontainerapps.io (UK South), in resource group
`mindaid-demo-rg`: Azure Container Apps (`mindaid-app`, pinned to exactly 1 instance because the database lives inside
the container), a container registry (`mindaidacrl6bhb`) holding the image, and the Azure AI Foundry model.
The AI key and cookie-signing key are Azure secrets, not in the image or in git. Data resets when the app restarts.

Redeploy after changing code (use the Azure CLI at `~/.azure-cli-venv/bin/az`, signed in with `az login`):

```bash
az acr build -r mindaidacrl6bhb -t mindaid:v2 .
az containerapp update -n mindaid-app -g mindaid-demo-rg --image mindaidacrl6bhb.azurecr.io/mindaid:v2
```

Use a new tag (v3, v4...) each time. To see logs: `az containerapp logs show -n mindaid-app -g mindaid-demo-rg --tail 50`.
To delete everything and stop all charges: `az group delete -n mindaid-demo-rg`.

## Known limitations (be upfront about these)

- Accounts are basic: no email verification, no password reset, no two-factor. Fine for a portfolio demo, not for real clinical use.
- The demo psychologist's password is public, so anyone can read every patient's entries. That is why the site says: fictional content only.
- Before a public deployment: set a real `SECRET_KEY`, serve over HTTPS and mark the cookie secure
  (`https_only=True` in `app/main.py`), and add a Postgres driver.
- Priority is an AI-generated sorting aid, not a monitored alert. The fake summaries are scripted.
- No clinical validation has been done. This is a UX/product prototype.
