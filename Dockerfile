# Container image for MindAId (built for Azure Container Apps later; nothing is deployed by this file).
FROM python:3.12-slim

WORKDIR /code

# Install libraries first so Docker can reuse this layer when only app code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Don't run as root inside the container.
RUN useradd --create-home appuser && chown -R appuser /code
USER appuser

# The platform tells the app which port to use via the PORT variable (default 8000).
ENV PORT=8000
EXPOSE 8000

# Container health check uses the /health endpoint.
HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"

# On start: create the demo users/entries (the database lives inside the container and resets on restart),
# then run the web server. --proxy-headers makes it trust Azure's front door about HTTPS.
CMD ["sh", "-c", "python scripts/seed.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
