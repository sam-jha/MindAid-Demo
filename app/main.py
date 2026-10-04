"""App entry point: creates the app, the tables, and wires the routes together."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app import models  # noqa: F401  (importing registers the tables)
from app.config import COOKIE_SECURE, SECRET_KEY
from app.database import Base, engine
from app.routes import auth, patient, psychologist

# Create tables if they don't exist yet (simple choice: no migration tool for v1).
Base.metadata.create_all(engine)

app = FastAPI(title="MindAId (demo prototype)")
# Session cookie is cleared when the browser closes (max_age=None).
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=None, https_only=COOKIE_SECURE)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

app.include_router(auth.router)
app.include_router(patient.router)
app.include_router(psychologist.router)


@app.get("/health")
def health():
    """Used later by Azure Container Apps to check the app is alive."""
    return {"status": "ok"}
