# =============================================
# DAP Production Image — API + dashboard in one image
# =============================================
# Build from the repo root:
#   docker build -f templates/docker/Dockerfile -t dap .
# The compose file (DOCKERCOMPOSE_PROD.yml) uses this image for both the
# API (uvicorn) and the dashboard (dap_dashboard.py).

FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# libpq5 for asyncpg/psycopg; curl kept for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (single deployable; see src/main.py)
COPY src/ ./src/
COPY conftest.py dap_dashboard.py start_dap.py ./

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8001 8081

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8001/api/health', timeout=3).status == 200 else 1)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
