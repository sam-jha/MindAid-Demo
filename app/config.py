"""All settings come from environment variables (see .env.example)."""
import os

from dotenv import load_dotenv

load_dotenv()  # reads a local .env file if there is one

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mindaid.db")
SUMMARISER_MODE = os.getenv("SUMMARISER_MODE", "fake")  # "fake" or "foundry"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
PORT = int(os.getenv("PORT", "8000"))

# Accounts / login
# True on Azure (HTTPS) so the login cookie is only sent over HTTPS. False for local http://localhost.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
# Pre-made demo accounts: shown on the login page so visitors can try the app without registering.
SHOW_DEMO_LOGINS = os.getenv("SHOW_DEMO_LOGINS", "true").lower() == "true"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "demo-password-1")  # not a secret: it is shown on the page

# Azure AI Foundry (only used when SUMMARISER_MODE=foundry)
AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT", "")
AZURE_AI_DEPLOYMENT = os.getenv("AZURE_AI_DEPLOYMENT", "")
AZURE_AI_API_KEY = os.getenv("AZURE_AI_API_KEY", "")  # a secret: keep it in .env / Azure secrets only
AZURE_AI_REGION = os.getenv("AZURE_AI_REGION", "")  # shown in the consent notice, e.g. "UK South"
